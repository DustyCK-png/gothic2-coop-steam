import json,os,pathlib,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parent
game=pathlib.Path('C:/Games/Gothic2Coop-TestClient');ipc=game/f'.intro-save-qa-{time.time_ns()}'
def read(p):
 try:return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
 except (PermissionError,json.JSONDecodeError):return {}
before={p.name for p in (game/'Saves').glob('savegame*')}
env=os.environ.copy();env.update(G2_COOP_QA='checkpoint',G2_COOP_CAMPAIGN=str(ipc),G2_COOP_CAMPAIGN_HOST='1')
pathlib.Path(str(ipc)+'.command').write_text(json.dumps({'op':'qa-finish','id':'intro'}),encoding='utf-8')
p=subprocess.Popen([str(game/'system/Gothic2.exe')],cwd=game/'system',env=env)
report={'status':'failed','scenario':'native autosave after Xardas dialogue, free slot only'}
try:
 end=time.monotonic()+120
 while time.monotonic()<end:
  if p.poll() is not None:raise RuntimeError('Game exited '+str(p.returncode))
  event=read(pathlib.Path(str(ipc)+'.event'))
  if event.get('event')=='save':
   slot=event['slot'];folder=game/'Saves'/f'savegame{slot}'
   assert folder.name not in before,'Existing slot overwritten'
   assert (folder/'SAVEDAT.SAV').exists() and (folder/'NEWWORLD.SAV').exists()
   assert read(pathlib.Path(str(ipc)+'.reply')).get('ok')
   time.sleep(5);assert p.poll() is None,'Game failed after autosave'
   report.update(status='passed',slot=slot,path=str(folder),stable_ms=5000);break
  time.sleep(.25)
 else:raise TimeoutError('Autosave did not complete')
except Exception as e:report['error']=str(e)
finally:
 if p.poll() is None:p.terminate();p.wait(timeout=10)
 report['dll_sha256']=__import__('hashlib').sha256((game/'system/Autorun/GothicCoop_G2A.dll').read_bytes()).hexdigest()
 (ROOT/'native-intro-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2),flush=True)
 if report['status']!='passed':raise SystemExit(1)
