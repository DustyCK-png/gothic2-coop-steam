import json,os,pathlib,subprocess,time,hashlib,ctypes
ROOT=pathlib.Path(__file__).resolve().parent
host=pathlib.Path('C:/Games/Gothic2Coop-GameplayQA');client=pathlib.Path('C:/Games/Gothic2Coop-TestClient')
ipc=client/f'.native-hostsave-qa-{time.time_ns()}'
ps=[];report={'status':'failed','transport':'two real Gothic processes, local ENet; IPC controller substitutes for relay'}
def wait(fn,seconds=120):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if any(p.poll() is not None for p in ps):raise RuntimeError('A game process exited: '+str([(p.pid,p.returncode) for p in ps]))
  try:
   value=fn()
   if value:return value
  except (json.JSONDecodeError,PermissionError):pass
  time.sleep(.25)
 raise TimeoutError('Native pair QA timed out')
def read(p):return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
def launch(role,game):
 qa=game/'GothicCoopQA.json'
 if qa.exists():qa.replace(qa.with_suffix('.previous.json'))
 env=os.environ.copy();env['G2_COOP_QA']=role
 if role=='client':env['G2_COOP_CAMPAIGN']=str(ipc);env['G2_COOP_CAMPAIGN_HOST']='0'
 p=subprocess.Popen([str(game/'system'/'Gothic2.exe')],cwd=game/'system',env=env,creationflags=0x00000004 if role=='client' else 0);ps.append(p);print('started',role,p.pid,flush=True)
 if role=='client':
  # QA only: winDoInstanceCheck exits with code 1 when its mapping already exists.
  # Change its verified JNE to JMP in this suspended process, never on disk.
  k=ctypes.WinDLL('kernel32',use_last_error=True);handle=ctypes.c_void_p(int(p._handle));address=ctypes.c_void_p(0x503607)
  data=ctypes.create_string_buffer(2);done=ctypes.c_size_t();old=ctypes.c_ulong()
  assert k.ReadProcessMemory(handle,address,data,2,ctypes.byref(done)) and data.raw==b'\x75\x08',data.raw.hex()
  assert k.VirtualProtectEx(handle,address,2,0x40,ctypes.byref(old))
  assert k.WriteProcessMemory(handle,address,b'\xeb\x08',2,ctypes.byref(done))
  protection=ctypes.c_ulong();assert k.VirtualProtectEx(handle,address,2,old.value,ctypes.byref(protection))
  k.FlushInstructionCache(handle,address,2)
  title=ctypes.c_void_p(0x89A7FC);titledata=ctypes.create_string_buffer(9)
  assert k.ReadProcessMemory(handle,title,titledata,9,ctypes.byref(done)) and titledata.raw==b'Gothic II'
  assert k.VirtualProtectEx(handle,title,9,0x40,ctypes.byref(old))
  assert k.WriteProcessMemory(handle,title,b'Gothic QA',9,ctypes.byref(done))
  assert k.VirtualProtectEx(handle,title,9,old.value,ctypes.byref(protection))
  for site in (0x502F22,0x5032D1):
   address=ctypes.c_void_p(site)
   assert k.ReadProcessMemory(handle,address,data,2,ctypes.byref(done)) and data.raw==b'\x75\x08',(hex(site),data.raw.hex())
   assert k.VirtualProtectEx(handle,address,2,0x40,ctypes.byref(old))
   assert k.WriteProcessMemory(handle,address,b'\xeb\x08',2,ctypes.byref(done))
   assert k.VirtualProtectEx(handle,address,2,old.value,ctypes.byref(protection))
   k.FlushInstructionCache(handle,address,2)
  assert ctypes.WinDLL('ntdll').NtResumeProcess(handle)==0
 wait(lambda:read(qa).get('role')==role);return p
def command(op,**kw):
 cmd=pathlib.Path(str(ipc)+'.command');reply=pathlib.Path(str(ipc)+'.reply')
 if reply.exists():reply.unlink()
 temp=pathlib.Path(str(cmd)+'.tmp');temp.write_text(json.dumps(dict(op=op,id=str(time.time_ns()),**kw)),encoding='utf-8');os.replace(temp,cmd)
 result=wait(lambda:read(reply));assert result.get('ok'),result;return result
def stop(p):
 p.terminate();p.wait(timeout=10);ps.remove(p)
try:
 pathlib.Path(str(ipc)+'.ready').write_text('{}')
 hp=launch('host',host);cp=launch('client',client)
 wait(lambda:read(host/'GothicCoopQA.json').get('players',0)>0 and read(client/'GothicCoopQA.json').get('players',0)>0)
 report['two_clients_connected']=True
 empty_slot=next(i for i in range(20,0,-1) if not (client/'Saves'/f'savegame{i}').exists())
 command('qa-save-local',slot=empty_slot)
 assert not (client/'Saves'/f'savegame{empty_slot}').exists(),'Client created a local save'
 report['client_manual_save_blocked']=True
 expected=command('qa-set')['hero']
 assert (client/'Saves/savegame20/SAVEDAT.SAV').exists(),'Missing baseline intro save fixture'
 assert command('qa-load-local',slot=20)['hero']==expected,'Client loaded its own different progress'
 report['client_manual_load_blocked']=True
 capture=command('capture');snapshot=capture['path'];assert capture['hero']==expected
 report['captured_while_connected']=True
 stop(cp);pathlib.Path(str(ipc)+'.ready').unlink()
 cp=launch('client',client)
 assert read(client/'GothicCoopQA.json').get('players',0)==0
 restored=command('restore',path=snapshot);assert restored['hero']==expected,(restored,expected)
 report['restored_hero']=restored['hero']
 time.sleep(5);assert cp.poll() is None,'Client failed after restore, before reconnect'
 report['stable_after_restore']=True
 pathlib.Path(str(ipc)+'.ready').write_text('{}')
 wait(lambda:read(client/'GothicCoopQA.json').get('players',0)>0)
 report['reconnected_after_restore']=True;report['status']='passed'
except Exception as e:report['error']=str(e)
finally:
 for p in reversed(ps.copy()):
  if p.poll() is None:stop(p)
 report['dll_sha256']=__import__('hashlib').sha256((host/'system/Autorun/GothicCoop_G2A.dll').read_bytes()).hexdigest()
 (ROOT/'native-pair-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
 if report['status']!='passed':raise SystemExit(1)
