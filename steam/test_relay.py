import json,os,pathlib,shutil,socket,subprocess,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
test=ROOT/'steam-tests'
processes=[]
logs=[]
report={'status':'failed','transport':'Steam API mock, not real Steam'}
def wait(predicate):
    end=time.monotonic()+20
    while time.monotonic()<end:
        value=predicate()
        if value:return value
        if any(p.poll() is not None for p in processes):raise RuntimeError('Relay exited')
        time.sleep(.1)
    raise TimeoutError('Relay timeout')
def launch(role,game,port):
    folder=test/role;folder.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'steam-build/Release/G2Steam.exe',folder)
    shutil.copy2(ROOT/'steam-build/Release/mock_steam_api.dll',folder/'steam_api.dll')
    env=os.environ.copy();env['KFX_MOCK_STEAM_NAME']='Host' if role=='host' else 'Client'
    env['KFX_MOCK_STEAM_PORT_BASE']='48300'
    logfile=folder/'relay.log';f=logfile.open('w');logs.append(f)
    p=subprocess.Popen([str(folder/'G2Steam.exe'),'host' if role=='host' else 'join','--game',str(game),'--port',str(port),'--no-launch'],cwd=folder,env=env,stdout=f,stderr=subprocess.STDOUT)
    processes.append(p);wait(lambda:'Configured Gothic II:' in logfile.read_text(errors='replace'))
try:
    port=39568
    host_game=test/'fake-host';client_game=test/'fake-client'
    for folder in (host_game,client_game):
        (folder/'system').mkdir(parents=True,exist_ok=True)
        (folder/'system/GothicCoopConfig.json').write_text(json.dumps({'server':'localhost','port':1234,'nickname':'Preserved setting'}))
    launch('host',host_game,port);launch('client',client_game,port)
    config=json.loads((client_game/'system/GothicCoopConfig.json').read_text())
    assert config['server']=='127.0.0.1' and config['nickname']=='Preserved setting'
    assert json.loads((client_game/'system/GothicCoopConfig.json.before-steam').read_text())['server']=='localhost'
    echo=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);echo.bind(('127.0.0.1',port));echo.settimeout(10)
    player=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);player.settimeout(10)
    report['packet_sizes']=[]
    for size in (1,64,1400,16000):
        data=os.urandom(size);player.sendto(data,('127.0.0.1',config['port']))
        incoming,address=echo.recvfrom(65536);assert incoming==data
        echo.sendto(incoming,address);reply,_=player.recvfrom(65536);assert reply==data
        report['packet_sizes'].append(size)
    echo.close();player.close();report['status']='passed'
except Exception as error:report['error']=str(error)
finally:
    for p in reversed(processes):
        if p.poll() is None:p.terminate();p.wait(timeout=10)
    for f in logs:f.close()
    (ROOT/'local/steam-relay-test.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))
    if report['status']!='passed':
        for role in ('host','client'):
            path=test/role/'relay.log'
            if path.exists():print(role,path.read_text(errors='replace')[-2000:])
        raise SystemExit(1)
