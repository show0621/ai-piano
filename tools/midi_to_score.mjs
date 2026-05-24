#!/usr/bin/env node
/**
 * 將 .mid 轉成 scores/*.json（欄位與 audio_processor.midi_to_web_notes 一致）
 * 用法: node tools/midi_to_score.mjs <input.mid> <output.json> [--title 簡單愛]
 */
import fs from "fs";
import path from "path";

const MIN_DURATION = 0.05;
const MIN_PITCH = 60; // C4
const MAX_PITCH = 83; // B5
const PLAY_MIN_DURATION = 0.08;

function round3(n) {
  return Math.round(n * 1000) / 1000;
}

function readStr(buf, off, len) {
  return buf.toString("ascii", off, off + len);
}

function readU32BE(buf, off) {
  return buf.readUInt32BE(off);
}

function readU16BE(buf, off) {
  return buf.readUInt16BE(off);
}

function readVLQ(buf, pos) {
  let value = 0;
  while (pos < buf.length) {
    const b = buf[pos++];
    value = (value << 7) | (b & 0x7f);
    if (!(b & 0x80)) break;
  }
  return [value, pos];
}

function ticksToSeconds(tick, division, tempoUs) {
  return (tick * tempoUs) / (division * 1_000_000);
}

function parseMidi(buffer) {
  if (readStr(buffer, 0, 4) !== "MThd") {
    throw new Error("不是標準 MIDI 檔 (缺少 MThd)");
  }
  const hdrLen = readU32BE(buffer, 4);
  const format = readU16BE(buffer, 8);
  const numTracks = readU16BE(buffer, 10);
  const division = readU16BE(buffer, 12);
  if (division & 0x8000) {
    throw new Error("不支援 SMPTE 時間碼格式");
  }
  let pos = 8 + hdrLen;
  const tracks = [];
  for (let t = 0; t < numTracks; t++) {
    if (readStr(buffer, pos, 4) !== "MTrk") {
      throw new Error(`Track ${t}: 缺少 MTrk`);
    }
    const trkLen = readU32BE(buffer, pos + 4);
    const trkStart = pos + 8;
    const trkEnd = trkStart + trkLen;
    let p = trkStart;
    let tick = 0;
    let tempoUs = 500_000; // 120 BPM
    let status = 0;
    const events = [];
    const active = new Map(); // key channel:pitch -> { startTick, vel }

    while (p < trkEnd) {
      const [delta, p2] = readVLQ(buffer, p);
      p = p2;
      tick += delta;

      let byte = buffer[p++];
      if (byte < 0x80) {
        p--;
        byte = status;
      } else {
        status = byte;
      }

      const cmd = byte & 0xf0;
      const ch = byte & 0x0f;

      if (cmd === 0x90 || cmd === 0x80) {
        const pitch = buffer[p++];
        const vel = buffer[p++];
        const key = `${ch}:${pitch}`;
        if (cmd === 0x90 && vel > 0) {
          active.set(key, { startTick: tick, vel });
        } else {
          const on = active.get(key);
          if (on) {
            events.push({
              pitch,
              startTick: on.startTick,
              endTick: tick,
              channel: ch,
            });
            active.delete(key);
          }
        }
      } else if (byte === 0xff) {
        const meta = buffer[p++];
        const [len, p3] = readVLQ(buffer, p);
        p = p3;
        if (meta === 0x51 && len === 3) {
          tempoUs =
            (buffer[p] << 16) | (buffer[p + 1] << 8) | buffer[p + 2];
        }
        p += len;
        status = 0;
      } else if (byte === 0xf0 || byte === 0xf7) {
        const [len, p3] = readVLQ(buffer, p);
        p = p3 + len;
        status = 0;
      } else if (cmd === 0xa0 || cmd === 0xb0 || cmd === 0xe0) {
        p += 2;
      } else if (cmd === 0xc0 || cmd === 0xd0) {
        p += 1;
      } else if (byte >= 0xf8) {
        // system real-time, ignore
      } else {
        // skip unknown
        status = 0;
      }
    }

    // 未關閉的音符：延伸到軌道末尾
    for (const [key, on] of active) {
      const pitch = Number(key.split(":")[1]);
      events.push({
        pitch,
        startTick: on.startTick,
        endTick: tick,
        channel: Number(key.split(":")[0]),
      });
    }

    tracks.push({ events, division, tempoUs });
    pos = trkEnd;
  }

  const allNotes = [];
  for (const trk of tracks) {
    const { events, division, tempoUs } = trk;
    for (const ev of events) {
      if (ev.channel === 9) continue; // 鼓組
      const start = ticksToSeconds(ev.startTick, division, tempoUs);
      const end = ticksToSeconds(ev.endTick, division, tempoUs);
      const dur = Math.max(end - start, MIN_DURATION);
      allNotes.push({
        pitch: ev.pitch,
        start_time: round3(start),
        end_time: round3(start + dur),
        duration: round3(dur),
      });
    }
  }

  allNotes.sort((a, b) => a.start_time - b.start_time);
  return allNotes;
}

/** 與 audio_processor.filter_notes 相同 */
function filterNotes(notes, maxNotes = 1200) {
  const cleaned = notes.filter(
    (n) =>
      n.pitch >= MIN_PITCH &&
      n.pitch <= MAX_PITCH &&
      n.duration >= PLAY_MIN_DURATION,
  );
  cleaned.sort((a, b) => a.start_time - b.start_time);
  if (cleaned.length <= maxNotes) return cleaned;
  const step = cleaned.length / maxNotes;
  return Array.from({ length: maxNotes }, (_, i) => cleaned[Math.floor(i * step)]);
}

/** 與 audio_processor.simplify_to_melody 相同 */
function simplifyToMelody(notes) {
  if (!notes.length) return notes;
  const window = 0.12;
  const sorted = [...notes].sort((a, b) => a.start_time - b.start_time);
  const melody = [];
  let i = 0;
  while (i < sorted.length) {
    const t0 = sorted[i].start_time;
    const group = [];
    while (i < sorted.length && sorted[i].start_time < t0 + window) {
      group.push(sorted[i]);
      i++;
    }
    if (group.length) {
      melody.push(group.reduce((a, b) => (a.pitch > b.pitch ? a : b)));
    }
  }
  return melody;
}

function main() {
  const args = process.argv.slice(2);
  if (args.length < 2) {
    console.error("用法: node tools/midi_to_score.mjs <input.mid> <output.json> [--title 名稱]");
    process.exit(1);
  }
  let title = "簡單愛";
  let fullTracks = false;
  const positional = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--title" && args[i + 1]) {
      title = args[++i];
    } else if (args[i] === "--full") {
      fullTracks = true;
    } else {
      positional.push(args[i]);
    }
  }
  const [inPath, outPath] = positional;
  if (!fs.existsSync(inPath)) {
    console.error("找不到 MIDI:", inPath);
    process.exit(1);
  }
  const buf = fs.readFileSync(inPath);
  let notes = parseMidi(buf);
  if (!fullTracks) {
    notes = simplifyToMelody(filterNotes(notes));
  }
  if (!notes.length) {
    console.error("MIDI 內沒有可用的音符");
    process.exit(1);
  }
  const last = notes[notes.length - 1];
  const durationEst = Math.ceil(last.start_time + last.duration);
  const payload = {
    title,
    meta: {
      id: "jianndanai",
      source: "midi",
      artist: "周杰倫",
      midi_file: path.basename(inPath),
    },
    notes,
  };
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(payload, null, 2), "utf8");
  console.log(`Wrote ${outPath}: ${notes.length} notes, ~${durationEst}s`);
}

main();
