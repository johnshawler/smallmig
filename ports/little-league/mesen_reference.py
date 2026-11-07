"""Run a fresh external game-state comparison in Mesen's headless runner."""
from pathlib import Path
import subprocess


def capture(mesen, rom, input_script, out, frames, timeout):
    steps = []
    for line in Path(input_script).read_text().splitlines():
        fields = line.split()
        if len(fields) == 2:
            steps.append('{%d,0x%x}' % (int(fields[0]), int(fields[1], 16)))
    selected = sorted({n for n in (1500, 6000, frames) if n <= frames})
    lua = 'local frame=0\nlocal steps={' + ','.join(steps) + '}\n'
    lua += 'local selected={' + ','.join('[%d]=true' % n for n in selected) + '}\n'
    lua += '''
emu.addEventCallback(function()
 frame=frame+1
 if frame%10000==0 then print('PROGRESS '..frame) end
 if selected[frame] then
  local ram={}
  for i=0,2047 do ram[#ram+1]=string.format('%02x',emu.read(i,emu.memType.nesInternalRam)) end
  print('RAM '..frame..' '..table.concat(ram))
 end
 if frame==FRAMES then emu.stop(0) end
end,emu.eventType.endFrame)
emu.addEventCallback(function()
 local m=0
 for _,s in ipairs(steps) do if s[1]<=frame then m=s[2] else break end end
 emu.setInput({a=(m&0x100)~=0,b=(m&1)~=0,select=(m&4)~=0,start=(m&8)~=0,
   up=(m&0x10)~=0,down=(m&0x20)~=0,left=(m&0x40)~=0,right=(m&0x80)~=0},0)
end,emu.eventType.inputPolled)
'''.replace('FRAMES', str(frames))
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    script = out/'mesen-reference.lua'
    script.write_text(lua)
    log = out/'mesen-reference.log'
    with log.open('w') as stream:
        result = subprocess.run([str(mesen), '--testRunner', '--enableStdout', '--timeout='+str(timeout),
                                 '--nes.port1.type=NesController', str(script), str(rom)],
                                stdout=stream, stderr=subprocess.STDOUT, timeout=timeout+30)
    if result.returncode:
        raise SystemExit('Mesen reference run failed; inspect '+str(log))
    states = {}
    for line in log.read_text().splitlines():
        if line.startswith('RAM '):
            _, frame, data = line.split()
            states[int(frame)] = bytes.fromhex(data)
    if set(states) != set(selected) or any(len(ram) != 2048 for ram in states.values()):
        raise SystemExit('Mesen did not produce all requested complete RAM states')
    return states


def compare(path, states):
    import struct
    data = Path(path).read_bytes()
    size = 8+2048+256+32+2048
    if len(data) % size:
        raise SystemExit('Truncated runtime state dump')
    runtime = {struct.unpack_from('<Q', data, i)[0]: data[i+8:i+2056]
               for i in range(0, len(data), size)}
    for frame, ram in sorted(states.items()):
        # Mesen labels completed frames starting at one; runtime hooks start at zero.
        actual = runtime.get(frame-1)
        if actual != ram:
            differences = sum(a != b for a, b in zip(actual or b'', ram))
            raise SystemExit(f'RAM mismatch at Mesen frame {frame}: {differences} differing bytes')
        print(f'Mesen frame {frame}: all 2048 game RAM bytes identical')
