#!/usr/bin/env python3
"""Measure source hardware timing and game update cadence in real Mesen.

The headless runner is unthrottled: wall-clock throughput is not NES speed.
Cartridge bytes and captures stay private; reports contain counts only.
"""
import argparse
import json
from pathlib import Path
import subprocess
from build import ROOT, HERE, cartridge


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom', required=True)
    p.add_argument('--mesen', required=True)
    p.add_argument('--frames', type=int, default=6000)
    p.add_argument('--first', type=int, default=1600)
    p.add_argument('--last', type=int, default=2200)
    a = p.parse_args()
    if not 1 <= a.first < a.last <= a.frames:
        p.error('Require 1 <= first < last <= frames')
    rom = cartridge(a.rom)
    out = ROOT/'build/little-league-original/speed'
    out.mkdir(parents=True, exist_ok=True)
    steps = []
    for line in (HERE/'vendor/tools/discovery/inputs/play_watchgame.txt').read_text().splitlines():
        fields = line.split()
        if len(fields) == 2:
            steps.append('{%d,0x%x}' % (int(fields[0]), int(fields[1], 16)))
    lua = 'local steps={'+','.join(steps)+'}\n'
    lua += 'local FIRST,LAST,FINAL=%d,%d,%d\n' % (a.first, a.last, a.frames)
    lua += '''local frame,dma=0,0
local hist,changedPixels,previous={}, {}, nil
local instructions,distinct,repeated=0,0,0
local lastChange=nil
local gaps={}
local active=false
emu.addMemoryCallback(function(addr)
 if active then hist[addr]=(hist[addr] or 0)+1; instructions=instructions+1 end
end,emu.callbackType.exec,0x8000,0xffff)
emu.addMemoryCallback(function() if active then dma=dma+1 end end,emu.callbackType.write,0x4014)
emu.addEventCallback(function()
 frame=frame+1
 local s=emu.getState()
 if frame==1 then print('CONFIG '..s.region..' '..s.clockRate) end
 print(string.format('FRAME %d %d %d',frame,s['cpu.cycleCount'],s['ppu.masterClock']))
 if frame>=FIRST and frame<=LAST then
  local pixels=emu.getScreenBuffer()
  if #pixels~=61440 then error('Expected unfiltered 256x240 Mesen framebuffer') end
  if previous then
   local changed=0
   for i=1,#pixels do if pixels[i]~=previous[i] then changed=changed+1 end end
   changedPixels[#changedPixels+1]=changed
   if changed==0 then repeated=repeated+1 else
    distinct=distinct+1
    if lastChange then local gap=frame-lastChange; gaps[gap]=(gaps[gap] or 0)+1 end
    lastChange=frame
   end
  end
  previous=pixels
 end
 active=frame>=FIRST and frame<LAST
 if frame==FINAL then
  print(string.format('COUNTS %d %d %d %d',instructions,dma,distinct,repeated))
  for pc,n in pairs(hist) do print(string.format('PC %04x %d',pc,n)) end
  for gap,n in pairs(gaps) do print(string.format('GAP %d %d',gap,n)) end
  print('PIXELS '..table.concat(changedPixels,','))
  emu.stop(0)
 end
end,emu.eventType.endFrame)
emu.addEventCallback(function()
 local m=0
 for _,s in ipairs(steps) do if s[1]<=frame then m=s[2] else break end end
 emu.setInput({a=(m&0x100)~=0,b=(m&1)~=0,select=(m&4)~=0,start=(m&8)~=0,
  up=(m&0x10)~=0,down=(m&0x20)~=0,left=(m&0x40)~=0,right=(m&0x80)~=0},0)
end,emu.eventType.inputPolled)
'''
    script = out/'mesen-speed.lua'
    script.write_text(lua)
    log = out/'mesen-speed.log'
    with log.open('w') as f:
        subprocess.run([str(Path(a.mesen).resolve()), '--testRunner', '--enableStdout', '--timeout=300',
                        '--nes.port1.type=NesController', str(script), str(rom)],
                       stdout=f, stderr=subprocess.STDOUT, timeout=330, check=True)
    frames, hist, gaps = {}, {}, {}
    config = counts = pixels = None
    for line in log.read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == 'CONFIG': config = fields[1:]
        elif fields[0] == 'FRAME': frames[int(fields[1])] = tuple(map(int, fields[2:]))
        elif fields[0] == 'COUNTS': counts = list(map(int, fields[1:]))
        elif fields[0] == 'PC': hist[fields[1]] = int(fields[2])
        elif fields[0] == 'GAP': gaps[fields[1]] = int(fields[2])
        elif fields[0] == 'PIXELS': pixels = list(map(int, fields[1].split(',')))
    if len(frames) != a.frames or counts is None or len(pixels or []) != a.last-a.first:
        raise SystemExit('Incomplete Mesen speed run; inspect '+str(log))
    intervals = [frames[i][1]-frames[i-1][1] for i in range(a.first+1, a.last+1)]
    cycles = frames[a.last][0]-frames[a.first][0]
    n = a.last-a.first
    clock = int(config[1])
    report = dict(region=config[0], cpu_clock_hz=clock, frame_window=[a.first,a.last],
                  measured_frames=n, cpu_cycles=cycles, cpu_cycles_per_frame=cycles/n,
                  source_fps=clock*n/cycles, source_frame_ms=1000*cycles/(clock*n),
                  ppu_master_ticks_per_frame={str(v):intervals.count(v) for v in sorted(set(intervals))},
                  nes_instructions=counts[0], oam_dma_writes=counts[1],
                  changed_pictures=counts[2], repeated_pictures=counts[3],
                  picture_blocks=[dict(frame_window=[a.first+i,a.first+min(i+200,n)],
                                       changed=sum(v>0 for v in pixels[i:i+200]),
                                       repeated=sum(v==0 for v in pixels[i:i+200]))
                                  for i in range(0,n,200)],
                  picture_change_gaps_frames=gaps, changed_pixels=dict(min=min(pixels),max=max(pixels),mean=sum(pixels)/n),
                  top_nes_pcs=[dict(pc=pc,instructions=count,share_percent=100*count/counts[0])
                               for pc,count in sorted(hist.items(),key=lambda x:-x[1])[:24]],
                  scope='Mesen emulated hardware clocks and original game cadence; unthrottled host runtime is not source speed')
    (out/'mesen-speed.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
