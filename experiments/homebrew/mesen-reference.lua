-- SPDX-License-Identifier: 0BSD
-- Own observation script: no Lua file/network/OS access. Records actual ROM state.
local frame, count = 0, 0
local before = nil
local function snapshot()
  local data = {}
  for address=0,255 do
    data[#data+1] = string.format('%02x', emu.read(address, emu.memType.nesDebug))
  end
  local state = emu.getState()
  return table.concat(data), state['cpu.a'] or -1, state['cpu.x'] or -1,
         state['cpu.ps'] or -1
end
emu.addMemoryCallback(function()
  local ram,a,x,ps = snapshot()
  before={ram=ram,a=a,x=x,ps=ps}
end, emu.callbackType.exec, 0xC6C6)
emu.addMemoryCallback(function()
  if before then
    local ram,a,x,ps = snapshot()
    print(string.format('SMALL_MIG_TRACE {"frame":%d,"before":"%s","after":"%s","a0":%d,"x0":%d,"ps0":%d,"a1":%d,"x1":%d,"ps1":%d}',
      frame,before.ram,ram,before.a,before.x,before.ps,a,x,ps))
    count=count+1
    before=nil
  end
end, emu.callbackType.exec, 0xC7ED)
emu.addEventCallback(function()
  emu.setInput({start=frame==60 or frame==61,
    left=frame>=90 and frame<125,
    right=frame>=130 and frame<195},0)
end, emu.eventType.inputPolled)
emu.addEventCallback(function()
  frame=frame+1
  if frame%30==0 then print(string.format('SMALL_MIG_FRAME %d state=%d buttons=%d',frame,emu.read(0,emu.memType.nesDebug),emu.read(10,emu.memType.nesDebug))) end
  if frame==240 then
    print(string.format('SMALL_MIG_COMPLETE {"frames":%d,"movement_calls":%d}',frame,count))
    emu.stop(count>0 and 0 or 2)
  end
end, emu.eventType.endFrame)
