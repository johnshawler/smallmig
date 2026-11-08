local frame=0
emu.addEventCallback(function()
 frame=frame+1
 if frame%120==0 then print('LLB_FRAME '..frame..' PC '..emu.getState()['cpu.pc']) end
 if frame==2400 or frame==3300 then
  local function dump(kind,n)
   local a={};for i=0,n-1 do a[#a+1]=string.format('%02x',emu.read(i,kind)) end;return table.concat(a)
  end
  print('PPU '..frame..' '..dump(emu.memType.nesPpuDebug,16384))
  print('OAM '..frame..' '..dump(emu.memType.nesSpriteRam,256))
  local pixels=emu.getScreenBuffer();local a={};for i=1,#pixels do a[#a+1]=string.format('%06x',pixels[i]&0xffffff) end
  print('RGB '..frame..' '..table.concat(a))
  for k,v in pairs(emu.getState()) do if string.find(k,'ppu') and (string.find(k,'ontrol') or string.find(k,'croll')) then print('STATE '..k..' '..tostring(v)) end end
 end
 if frame%300==0 then
  local png=emu.takeScreenshot()
  print('PNG '..frame..' '..(png:gsub('.',function(c)return string.format('%02x',string.byte(c))end)))
 end
 if frame==3600 then emu.stop(0) end
end,emu.eventType.endFrame)
emu.addEventCallback(function()
 local a=(frame==180 or frame==181 or frame==400 or frame==401 or frame==600 or frame==601 or frame==800 or frame==801 or frame==1000 or frame==1001 or frame==1200 or frame==1201 or frame==1600 or frame==1601 or frame==1900 or frame==1901)
 emu.setInput({start=frame==60 or frame==61 ,down=frame==145 or frame==146,a=a,b=frame==1500 or frame==1501 or frame==1800 or frame==1801},0)
end,emu.eventType.inputPolled)
