import ctypes,json,os,pathlib,subprocess,time,sys,hashlib
ROOT=pathlib.Path(__file__).resolve().parent
games=[pathlib.Path('C:/Games/Gothic2Coop-GameplayQA'),pathlib.Path('C:/Games/Gothic2Coop-TestClient')]
ps=[];report={'status':'failed','transport':'two real Gothic II clients, local ENet'}
report['dll_sha256']=hashlib.sha256((games[0]/'system/Autorun/GothicCoop_G2A.dll').read_bytes()).hexdigest()
cache={}
def read(path):
 try:
  if not path.exists():return {}
  value=json.loads(path.read_text(encoding='utf-8'));cache[str(path)]=value;return value
 except (PermissionError,json.JSONDecodeError):return cache.get(str(path),{})
def wait(fn,seconds=30):
 end=time.monotonic()+seconds
 while time.monotonic()<end:
  if any(p.poll() is not None for p in ps):raise RuntimeError('Game exited '+str([(p.pid,p.returncode) for p in ps]))
  value=fn()
  if value:return value
  time.sleep(.15)
 raise TimeoutError('Native party QA timeout')
def patch_client(p):
 k=ctypes.WinDLL('kernel32',use_last_error=True);handle=ctypes.c_void_p(int(p._handle));done=ctypes.c_size_t();old=ctypes.c_ulong();protection=ctypes.c_ulong()
 for site in (0x503607,0x502F22,0x5032D1):
  address=ctypes.c_void_p(site);data=ctypes.create_string_buffer(2)
  assert k.ReadProcessMemory(handle,address,data,2,ctypes.byref(done)) and data.raw==b'\x75\x08'
  assert k.VirtualProtectEx(handle,address,2,0x40,ctypes.byref(old));assert k.WriteProcessMemory(handle,address,b'\xeb\x08',2,ctypes.byref(done));assert k.VirtualProtectEx(handle,address,2,old.value,ctypes.byref(protection));k.FlushInstructionCache(handle,address,2)
 title=ctypes.c_void_p(0x89A7FC);assert k.VirtualProtectEx(handle,title,9,0x40,ctypes.byref(old));assert k.WriteProcessMemory(handle,title,b'Gothic QA',9,ctypes.byref(done));assert k.VirtualProtectEx(handle,title,9,old.value,ctypes.byref(protection));assert ctypes.WinDLL('ntdll').NtResumeProcess(handle)==0
def launch(index):
 game=games[index];system=game/'system'
 cache.pop(str(system/'PartyQA.state'),None)
 for name in ('PartyQA.command','PartyQA.reply','PartyQA.state'):
  p=system/name
  if p.exists():p.replace(p.with_suffix('.previous'))
 env=os.environ.copy();env['G2_COOP_QA']='party-host' if index==0 else 'party-client';env.pop('G2_COOP_CAMPAIGN',None);env.pop('G2_COOP_CAMPAIGN_HOST',None);env['G2_COOP_QA_FAULT']=sys.argv[1] if len(sys.argv)>1 and index==0 else ''
 p=subprocess.Popen([str(system/'Gothic2.exe')],cwd=system,env=env,creationflags=4 if index else 0);ps.append(p);print('started',index,p.pid,flush=True)
 if index:patch_client(p)
 wait(lambda:read(system/'PartyQA.state').get('finished'));time.sleep(2)
def state(i):return read(games[i]/'system/PartyQA.state')
def command(i,op,**kw):
 system=games[i]/'system';key=str(time.time_ns());path=system/'PartyQA.command';tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(dict(id=key,op=op,**kw)),encoding='utf-8');os.replace(tmp,path)
 reply=wait(lambda: (lambda v:v if v.get('id')==key else None)(read(system/'PartyQA.reply')))
 assert reply['ok'],reply;return reply
def visible(i):
 puppets=state(i).get('puppets',[])
 return puppets and all(p['npc'] and p['model'] and p['world'] and p['leaf']>0 and p['visible'] for p in puppets)
try:
 launch(0);launch(1)
 assert state(0)['core_count']>=233,state(0)['core_count']
 command(0,'start');time.sleep(.5);command(1,'start')
 wait(lambda:state(0).get('ready') and state(1).get('ready') and visible(0) and visible(1))
 report['both_player_models_visible']=True
 before=[state(i)['xp'] for i in (0,1)]
 command(0,'xp',amount=101)
 wait(lambda:all(state(i)['xp']==before[i]+101 for i in (0,1)))
 report['host_reward_shared_once']=True
 command(0,'repeat-xp');time.sleep(1);assert all(state(i)['xp']==before[i]+101 for i in (0,1))
 report['duplicate_reward_ignored']=True
 before=[state(i)['xp'] for i in (0,1)]
 command(1,'xp',amount=103)
 wait(lambda:all(state(i)['xp']==before[i]+103 for i in (0,1)))
 report['client_reward_shared_once']=True
 before=[state(i)['xp'] for i in (0,1)]
 command(1,'xp',amount=103)
 wait(lambda:all(state(i)['xp']==before[i]+103 for i in (0,1)))
 report['equal_legitimate_rewards_preserved']=True
 command(0,'near-level');command(1,'near-level');time.sleep(.5)
 old=[(state(i)['level'],state(i)['lp']) for i in (0,1)]
 command(0,'xp',amount=25)
 wait(lambda:all(state(i)['level']==old[i][0]+1 and state(i)['lp']==old[i][1]+10 for i in (0,1)))
 report['native_level_up_and_learning_points']=True
 command(0,'puppet-cycle');wait(lambda:visible(0));report['distance_respawn_and_gear']=True
 command(1,'dialogue',npc='NONE_100_XARDAS');wait(lambda:state(0).get('owner')=='FRIEND_1' and state(1).get('owner')=='FRIEND_1')
 blocked=command(0,'dialogue',npc='BAU_950_LOBART')['state']
 assert blocked['owner']=='FRIEND_1' and blocked['finished'],'Host started a second dialogue'
 report['exclusive_dialogue']=True
 command(1,'real-quest');assert command(1,'finish')['state']['quest']['globals']['MIS_LOBART_RUEBEN']==[1],'Real quest accept did not start mission'
 wait(lambda:state(0).get('quest',{}).get('globals',{}).get('MIS_LOBART_RUEBEN')==[1])
 report['native_lobart_quest_accepted_and_shared']=True
 command(1,'dialogue',npc='NONE_100_XARDAS');wait(lambda:state(1).get('owner')=='FRIEND_1');command(1,'quest',value=1);command(1,'finish')
 wait(lambda:state(0).get('owner')=='' and state(0).get('quest',{}).get('globals',{}).get('MIS_LOBART_RUEBEN')==[1])
 wait(lambda:state(1).get('owner')=='')
 assert any(t['title']=='QA: shared Lobart quest' for t in state(0)['quest']['journal'])
 report['client_quest_flag_and_journal_shared']=True
 command(0,'reject-invalid');report['invalid_quest_packet_atomic']=True
 command(1,'dialogue',npc='NONE_100_XARDAS');wait(lambda:state(1).get('owner')=='FRIEND_1')
 command(1,'lease-pause')
 wait(lambda:state(1).get('finished') and state(1).get('owner')=='LEASE_EXPIRED',20)
 wait(lambda:state(0).get('owner')=='',20)
 report['lost_lease_closes_dialogue']=True
 before=[state(i)['xp'] for i in (0,1)]
 result=command(0,'prepare-victim');report['combat_bot_victim']=result.get('victim');time.sleep(2);result=command(0,'kill',npc=result['victim']);report['combat_native_dead']=result.get('dead')
 wait(lambda:all(state(i)['xp']>before[i] for i in (0,1)),20)
 report['native_combat_reward_shared']=True
 before=[state(i)['xp'] for i in (0,1)]
 result=command(1,'prepare-victim',exclude=report['combat_bot_victim']);report['client_combat_victim']=result['victim'];time.sleep(2);command(1,'kill',npc=result['victim'])
 wait(lambda:all(state(i)['xp']>before[i] for i in (0,1)),20)
 assert state(0)['xp']-before[0]==state(1)['xp']-before[1]
 report['client_combat_reward_shared_once']=True
 before=[state(i)['xp'] for i in (0,1)]
 command(1,'xp',amount=103)
 wait(lambda:all(state(i)['xp']==before[i]+103 for i in (0,1)))
 report['script_reward_after_combat_preserved']=True
 command(0,'save-ledger');assert (games[0]/'system/PartyQA-ledger/COOPGAME.SAV').exists();report['ledger_archivable']=True
 time.sleep(5);report['status']='passed'
except Exception as e:report['error']=str(e);report['states']=[state(i) for i in (0,1)]
finally:
 for p in reversed(ps):
  if p.poll() is None:p.terminate();p.wait(timeout=10)
 (ROOT/('party-mutation-'+sys.argv[1]+'.json' if len(sys.argv)>1 else 'party-test.json')).write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
 print(json.dumps({k:v for k,v in report.items() if k!='states'},indent=2),flush=True)
 if report['status']!='passed':raise SystemExit(1)
