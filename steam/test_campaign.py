"""Real relay processes + mock Steam; the game's native IPC is simulated here."""
import hashlib,json,os,pathlib,shutil,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
TEST=ROOT/'campaign-tests'/str(time.time_ns())
processes=[];logs=[];report={'status':'failed','transport':'mock Steam; not a two-account live test'}
def wait(predicate,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  try:value=predicate()
  except (PermissionError,FileNotFoundError,json.JSONDecodeError):value=False
  if value:return value
  if any(p.poll() is not None for p in processes):raise RuntimeError('Relay exited')
  time.sleep(.03)
 raise TimeoutError('Campaign test timed out')
def write(path,data):
 tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data));os.replace(tmp,path)
def launch(role,game):
 folder=TEST/role;folder.mkdir(parents=True,exist_ok=True)
 shutil.copy2(ROOT/'steam-build/Release/G2Steam.exe',folder/'G2Steam.exe')
 shutil.copy2(ROOT/'steam-build/Release/mock_steam_api.dll',folder/'steam_api.dll')
 env=os.environ.copy();env['KFX_MOCK_STEAM_NAME']='Host' if role=='host' else 'Client';env['KFX_MOCK_STEAM_PORT_BASE']='48700';env['G2_MOCK_HOST_SAVES']='1'
 log=(folder/f'{time.time_ns()}.log').open('w');logs.append(log)
 p=subprocess.Popen([str(folder/'G2Steam.exe'),'host' if role=='host' else 'join','--game',str(game),'--no-launch','--host-saves'],cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT)
 processes.append(p);ipc=game/f'.g2campaign-{p.pid}'
 wait(lambda:pathlib.Path(str(ipc)+'.status').exists());return ipc
def status(ipc,state):
 path=pathlib.Path(str(ipc)+'.status')
 return path.exists() and json.loads(path.read_text(encoding="utf-8")).get('state')==state
def event(ipc,kind,slot=1):write(pathlib.Path(str(ipc)+'.event'),{'event':kind,'slot':slot})
def command(ipc):
 path=pathlib.Path(str(ipc)+'.command');wait(path.exists);data=json.loads(path.read_text(encoding="utf-8"));path.unlink();return data
def reply(ipc,cmd,**kw):write(pathlib.Path(str(ipc)+'.reply'),dict(op=cmd['op'],id=cmd['id'],ok=True,**kw))
def stop():
 for p in reversed(processes):
  if p.poll() is None:p.terminate();p.wait(timeout=10)
 processes.clear()
def hashes(folder):return {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.glob('*.SAV')}
try:
 host=TEST/'host-game';client=TEST/'client-game'
 for game in (host,client):
  (game/'system').mkdir(parents=True);(game/'system/GothicCoopConfig.json').write_text('{"server":"localhost","port":1234}')
 hostslot=host/'Saves/savegame1';hostslot.mkdir(parents=True)
 (hostslot/'NEWWORLD.SAV').write_bytes(b'host world revision 1')
 snapshot=client/'Saves/coop-capture-fixture';snapshot.mkdir(parents=True)
 for name,size in [('NEWWORLD.SAV',1600000),('SAVEDAT.SAV',480000),('SAVEHDR.SAV',22)]: (snapshot/name).write_bytes(os.urandom(size))
 expected=hashes(snapshot)
 hi=launch('host',host);event(hi,'new');ci=launch('client',client)
 wait(lambda:status(ci,'fresh'));event(hi,'save')
 cmd=command(ci);assert cmd['op']=='capture';reply(ci,cmd,path=str(snapshot))
 wait(lambda:status(hi,'complete'),60)
 index=json.loads((host/'CoopHostSaves/slot-1.json').read_text(encoding="utf-8"));generation=index['generation']
 profile=host/'CoopHostSaves'/generation/'players/76561198000000002'
 assert hashes(profile)==expected;report['upload_checksum_verified']=True
 wait(lambda:not snapshot.exists());report['client_upload_cache_removed']=True
 stop();hi=launch('host',host);event(hi,'load');ci=launch('client',client)
 cmd=command(ci);assert cmd['op']=='restore';restored=pathlib.Path(cmd['path']);assert hashes(restored)==expected
 assert not pathlib.Path(str(ci)+'.ready').exists();reply(ci,cmd)
 wait(lambda:pathlib.Path(str(ci)+'.ready').exists());report['restore_before_connection']=True
 assert not restored.exists();report['client_download_cache_removed']=True
 stop();hi=launch('host',host);event(hi,'load');wait(lambda:status(hi,'loaded'))
 (hostslot/'NEWWORLD.SAV').write_bytes(b'host world revision 2, friend offline')
 event(hi,'save');wait(lambda:status(hi,'complete'))
 index=json.loads((host/'CoopHostSaves/slot-1.json').read_text(encoding="utf-8"));profile=host/'CoopHostSaves'/index['generation']/'players/76561198000000002'
 assert hashes(profile)==expected;report['offline_friend_preserved']=True
 stop();(hostslot/'NEWWORLD.SAV').write_bytes(b'changed outside a complete checkpoint')
 hi=launch('host',host);event(hi,'load');wait(lambda:status(hi,'blocked'));ci=launch('client',client)
 time.sleep(1);assert not pathlib.Path(str(ci)+'.ready').exists();assert not pathlib.Path(str(ci)+'.command').exists()
 report['mismatched_host_save_blocked']=True
 event(hi,'new');wait(lambda:status(ci,'fresh'))
 event(hi,'save');cmd=command(ci);assert cmd['op']=='capture'
 wait(lambda:(host/'CoopHostSaves/slot-1.pending.json').exists())
 assert json.loads((host/'CoopHostSaves/slot-1.json').read_text(encoding='utf-8'))==index
 stop();hi=launch('host',host);event(hi,'load');wait(lambda:status(hi,'blocked'))
 ci=launch('client',client);time.sleep(1);assert not pathlib.Path(str(ci)+'.ready').exists()
 report['interrupted_upload_not_committed']=True;report['status']='passed'
except Exception as e:report['error']=str(e)
finally:
 stop()
 for f in logs:f.close()
 (ROOT/'campaign-test.json').write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2))
 if report['status']!='passed':
  for f in TEST.glob('*/*.log'):print(f, f.read_text(errors='replace')[-1500:])
  raise SystemExit(1)
