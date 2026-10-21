// SPDX-License-Identifier: MIT
// Experimental host-owned checkpoints. Steam sender identities are supplied by the relay.
#define NOMINMAX
#include <windows.h>
#include <bcrypt.h>
#include <filesystem>
#include <fstream>
#include <map>
#include <set>
#include <deque>
#include <vector>
#include <string>
#include <algorithm>
#include <cstdio>
#include <nlohmann/json.hpp>
namespace {
namespace fs=std::filesystem;using J=nlohmann::json;using ID=unsigned long long;
using Send=int(*)(ID,const void*,int);
fs::path root,base,ipc;bool hosting=false,enabled=false,worldReady=false,joinReady=false,blocked=false;
ID self=0,owner=0;Send sendPacket=nullptr;unsigned sequence=0;
std::map<std::string,fs::path> uploaded;fs::path restoredCache;std::set<ID> clients;std::string active,waitingRestore;J pending;DWORD deadline=0;
struct Incoming {std::string id;fs::path dir;J files;std::map<std::string,size_t> offsets;};
std::map<ID,Incoming> incoming;
struct Outgoing {ID peer;std::string id;fs::path dir;J files;size_t file=0,offset=0;int phase=0;};
std::deque<Outgoing> outgoing;
constexpr size_t MAX_TOTAL=256*1024*1024,MAX_FILE=128*1024*1024,CHUNK=16384;
void log(const std::string& message){std::ofstream(root/"system/HostCampaign.log",std::ios::app)<<GetTickCount()<<" "<<message<<"\n";}
J read(const fs::path& p){std::ifstream in(p);if(!in)return J();return J::parse(in);}
void write(const fs::path& p,const J& value){fs::create_directories(p.parent_path());auto tmp=p;tmp+=".tmp";{std::ofstream out(tmp,std::ios::binary|std::ios::trunc);out<<value.dump(2);if(!out)throw std::runtime_error("Cannot write campaign metadata");}bool committed=false;for(int attempt=0;attempt<20&&!committed;++attempt){committed=MoveFileExW(tmp.c_str(),p.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;if(!committed)Sleep(2);}if(!committed)throw std::runtime_error("Cannot commit campaign metadata");}
std::string token(){return std::to_string(GetTickCount64())+"-"+std::to_string(GetCurrentProcessId())+"-"+std::to_string(++sequence);}
bool safe(const std::string& name){if(name.empty()||name.size()>64||name.find("..")!=std::string::npos)return false;for(unsigned char c:name)if(!isalnum(c)&&c!='_'&&c!='-'&&c!='.')return false;return name.size()>4&&_stricmp(name.c_str()+name.size()-4,".SAV")==0;}
std::string sha(const fs::path& p){BCRYPT_ALG_HANDLE a=nullptr;BCRYPT_HASH_HANDLE h=nullptr;unsigned char digest[32];if(BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,nullptr,0)<0)throw std::runtime_error("SHA256 unavailable");if(BCryptCreateHash(a,&h,nullptr,0,nullptr,0,0)<0){BCryptCloseAlgorithmProvider(a,0);throw std::runtime_error("SHA256 init failed");}std::ifstream in(p,std::ios::binary);char b[65536];while(in){in.read(b,sizeof b);auto n=in.gcount();if(n&&BCryptHashData(h,(PUCHAR)b,(ULONG)n,0)<0)throw std::runtime_error("SHA256 failed");}if(!in.eof()||BCryptFinishHash(h,digest,32,0)<0)throw std::runtime_error("Cannot hash save file");BCryptDestroyHash(h);BCryptCloseAlgorithmProvider(a,0);std::string result;const char* hex="0123456789abcdef";for(auto c:digest){result+=hex[c>>4];result+=hex[c&15];}return result;}
J describe(const fs::path& dir){J files=J::array();size_t total=0;for(auto& e:fs::directory_iterator(dir)){if(!e.is_regular_file()||e.is_symlink())continue;auto name=e.path().filename().string();if(!safe(name))continue;auto size=e.file_size();if(size>MAX_FILE||(total+=size)>MAX_TOTAL)throw std::runtime_error("Snapshot exceeds limits");files.push_back({{"name",name},{"size",size},{"sha256",sha(e.path())}});}std::sort(files.begin(),files.end(),[](const J&a,const J&b){return a["name"]<b["name"];});if(files.empty()||files.size()>64)throw std::runtime_error("Invalid snapshot file count");return files;}
void copy(const fs::path& from,const fs::path& to,const J& files){fs::create_directories(to);for(auto& f:files)fs::copy_file(from/f.at("name").get<std::string>(),to/f.at("name").get<std::string>(),fs::copy_options::none);if(describe(to)!=files)throw std::runtime_error("Snapshot changed during copy");}
bool send(ID peer,const J& message){auto bytes=J::to_bson(message);return sendPacket(peer,bytes.data(),(int)bytes.size())==1;}
void status(const std::string& state,const std::string& detail=""){write(ipc.string()+".status",{{"state",state},{"detail",detail}});log(state+": "+detail);}
void command(const J& cmd){if(fs::exists(ipc.string()+".command"))throw std::runtime_error("Previous native save command still pending");write(ipc.string()+".command",cmd);}
void enqueue(ID peer,const std::string& id,const fs::path& dir){outgoing.push_back({peer,id,dir,describe(dir)});}
void cleanCache(const fs::path& dir){
 if(dir.empty())return;
 try{
  auto name=dir.filename().string();
  if(name.rfind("coop-capture-",0)!=0&&name.rfind("coop-received-",0)!=0&&name.rfind("coop-before-restore-",0)!=0)throw std::runtime_error("Unexpected cache name");
  if(!fs::equivalent(dir.parent_path(),root/"Saves")||fs::is_symlink(dir))throw std::runtime_error("Cache outside save root");
  if(!fs::exists(dir))return;
  std::vector<fs::path> files;
  for(auto& item:fs::directory_iterator(dir)){if(item.is_symlink()||!item.is_regular_file()||!safe(item.path().filename().string()))throw std::runtime_error("Unexpected cache contents");files.push_back(item.path());}
  for(auto& file:files)fs::remove(file);
  fs::remove(dir);
 }catch(const std::exception& e){log(std::string("Temporary cache retained: ")+e.what());}
}
fs::path slotpath(int slot){if(slot<0||slot>20)throw std::runtime_error("Invalid host slot");return root/"Saves"/(slot==0?"quicksave":"savegame"+std::to_string(slot));}
void select(int slot){active.clear();worldReady=true;blocked=false;auto signature=describe(slotpath(slot));auto index=read(base/("slot-"+std::to_string(slot)+".json"));auto unfinished=read(base/("slot-"+std::to_string(slot)+".pending.json"));if(unfinished.is_object()&&unfinished.value("host",J())==signature){blocked=true;status("blocked","This save has an unfinished friend checkpoint.");return;}if(index.is_object()&&index.value("host",J())==signature){active=index.at("generation");status("loaded",active);}else {blocked=index.is_object()||fs::exists(base/("slot-"+std::to_string(slot)+".pending.json"));status(blocked?"blocked":"new-campaign","This slot has no matching complete friend checkpoint.");}}
void offer(ID peer){if(!worldReady||blocked){send(peer,{{"op","wait"}});return;}if(active.empty()){send(peer,{{"op","fresh"}});return;}auto profile=base/active/"players"/std::to_string(peer);if(fs::exists(profile))enqueue(peer,"restore-"+token(),profile);else send(peer,{{"op","fresh"}});}
void commit(){if(pending.is_null())return;for(auto& item:pending["players"].items())if(!item.value().get<bool>())return;int slot=pending.at("slot");if(describe(slotpath(slot))!=pending.at("host"))throw std::runtime_error("Host slot changed before all player uploads finished");std::string generation=pending.at("generation");write(base/generation/"manifest.json",pending);write(base/("slot-"+std::to_string(slot)+".json"),{{"generation",generation},{"host",pending.at("host")}});fs::remove(base/("slot-"+std::to_string(slot)+".pending.json"));active=generation;worldReady=true;blocked=false;status("complete",generation);pending=J();}
void save(int slot){if(!pending.is_null()){status("incomplete","A newer save replaced an unfinished checkpoint.");pending=J();incoming.clear();}std::string generation="generation-"+token();auto files=describe(slotpath(slot));copy(slotpath(slot),base/generation/"host",files);pending={{"generation",generation},{"slot",slot},{"host",files},{"players",J::object()}};auto previous=base/active/"players";if(!active.empty()&&fs::exists(previous))for(auto& e:fs::directory_iterator(previous)){if(!e.is_directory()||e.is_symlink())continue;auto name=e.path().filename().string();if(name.find_first_not_of("0123456789")!=std::string::npos)continue;copy(e.path(),base/generation/"players"/name,describe(e.path()));pending["players"][name]=true;}for(ID id:clients){pending["players"][std::to_string(id)]=false;send(id,{{"op","capture"},{"id",generation}});}write(base/("slot-"+std::to_string(slot)+".pending.json"),pending);deadline=GetTickCount()+120000;status("saving",generation);commit();}
void event(){auto path=fs::path(ipc.string()+".event");if(!fs::exists(path))return;auto e=read(path);fs::remove(path);if(!hosting)return;std::string kind=e.value("event","");if(kind=="save")save(e.at("slot"));else if(kind=="load"){select(e.at("slot"));for(ID id:clients)offer(id);}else if(kind=="new"){active.clear();worldReady=true;blocked=false;for(ID id:clients)offer(id);}}
void nativeReply(){auto path=fs::path(ipc.string()+".reply");if(!fs::exists(path))return;auto reply=read(path);fs::remove(path);std::string id=reply.value("id","");if(!reply.value("ok",false)){status("error",reply.value("error","Native save failed"));return;}if(reply.value("op","")=="capture"){fs::path dir=fs::u8path(reply.at("path").get<std::string>());if(dir.parent_path()!=root/"Saves"&&dir.parent_path()!=root/"SAVES")throw std::runtime_error("Capture outside private save root");if(dir.filename().string().rfind("coop-capture-",0)!=0)throw std::runtime_error("Invalid private capture folder");uploaded[id]=dir;enqueue(owner,id,dir);}else if(reply.value("op","")=="restore"&&id==waitingRestore){cleanCache(restoredCache);if(reply.contains("previous_cache"))cleanCache(fs::u8path(reply.at("previous_cache").get<std::string>()));waitingRestore.clear();joinReady=true;status("restored");}}
void transmit(){if(outgoing.empty())return;auto& t=outgoing.front();if(t.phase==0){if(send(t.peer,{{"op","begin"},{"id",t.id},{"files",t.files}}))t.phase=1;return;}if(t.file>=t.files.size()){if(send(t.peer,{{"op","end"},{"id",t.id}}))outgoing.pop_front();return;}auto f=t.files[t.file];size_t size=f.at("size");if(t.offset>=size){++t.file;t.offset=0;return;}std::ifstream in(t.dir/f.at("name").get<std::string>(),std::ios::binary);in.seekg(t.offset);std::vector<uint8_t> bytes(std::min(CHUNK,size-t.offset));in.read((char*)bytes.data(),bytes.size());if((size_t)in.gcount()!=bytes.size())throw std::runtime_error("Snapshot disappeared during upload");if(send(t.peer,{{"op","chunk"},{"id",t.id},{"name",f["name"]},{"offset",t.offset},{"bytes",J::binary(bytes)}}))t.offset+=bytes.size();}
void receive(ID peer,const J& msg){std::string op=msg.at("op");if(hosting&&op=="hello"){clients.insert(peer);offer(peer);return;}if(!hosting&&op=="fresh"){joinReady=true;status("fresh");return;}if(!hosting&&op=="wait")return;
 if(!hosting&&op=="capture"){std::string id=msg.at("id");if(id.size()>80)throw std::runtime_error("Invalid checkpoint id");command({{"op","capture"},{"id",id}});return;}
 if(op=="begin"){
  std::string id=msg.at("id");if(id.size()>80||id.find_first_not_of("abcdefghijklmnopqrstuvwxyz0123456789-")!=std::string::npos)throw std::runtime_error("Invalid transfer id");
  if(hosting&&(pending.is_null()||pending.at("generation")!=id||!pending["players"].contains(std::to_string(peer))||pending["players"][std::to_string(peer)].get<bool>()))throw std::runtime_error("Unsolicited upload");
  if(!hosting&&(id.rfind("restore-",0)!=0||!waitingRestore.empty()||joinReady))throw std::runtime_error("Unsolicited restore");
  J files=msg.at("files");if(!files.is_array()||files.empty()||files.size()>64)throw std::runtime_error("Invalid file list");size_t total=0;std::set<std::string> names;
  for(auto& f:files){auto name=f.at("name").get<std::string>();auto size=f.at("size").get<size_t>();std::string hash=f.at("sha256");if(!safe(name)||!names.insert(name).second||size>MAX_FILE||(total+=size)>MAX_TOTAL||hash.size()!=64||hash.find_first_not_of("0123456789abcdef")!=std::string::npos)throw std::runtime_error("Unsafe save file");}
  if(incoming.count(peer))throw std::runtime_error("Duplicate transfer");auto dir=hosting?base/pending.at("generation").get<std::string>()/"incoming"/std::to_string(peer):root/"Saves"/("coop-received-"+token());if(fs::exists(dir))throw std::runtime_error("Transfer directory exists");fs::create_directories(dir);Incoming t{id,dir,files,{}};for(auto& f:files){std::string name=f.at("name");t.offsets[name]=0;std::ofstream(dir/name,std::ios::binary);}incoming.emplace(peer,std::move(t));return;
 }
 auto it=incoming.find(peer);if(it==incoming.end()||msg.value("id","")!=it->second.id)throw std::runtime_error("Unknown save transfer");auto& t=it->second;
 if(op=="chunk"){std::string name=msg.at("name");if(!t.offsets.count(name)||msg.at("offset").get<size_t>()!=t.offsets[name]||!msg.at("bytes").is_binary())throw std::runtime_error("Invalid save chunk");auto bytes=msg.at("bytes").get_binary();auto f=std::find_if(t.files.begin(),t.files.end(),[&](const J& v){return v["name"]==name;});if(bytes.size()>CHUNK||t.offsets[name]+bytes.size()>f->at("size").get<size_t>())throw std::runtime_error("Oversized save chunk");std::ofstream out(t.dir/name,std::ios::binary|std::ios::app);out.write((const char*)bytes.data(),bytes.size());if(!out)throw std::runtime_error("Save disk write failed");t.offsets[name]+=bytes.size();return;}
 if(op=="end"){if(describe(t.dir)!=t.files)throw std::runtime_error("Save checksum mismatch");if(hosting){auto generation=base/pending.at("generation").get<std::string>();auto dest=generation/"players"/std::to_string(peer);fs::create_directories(dest.parent_path());if(fs::exists(dest)){auto backup=generation/"previous"/std::to_string(peer);fs::create_directories(backup.parent_path());fs::rename(dest,backup);}fs::rename(t.dir,dest);pending["players"][std::to_string(peer)]=true;send(peer,{{"op","stored"},{"id",t.id}});incoming.erase(it);commit();}else{waitingRestore=t.id;restoredCache=t.dir;command({{"op","restore"},{"id",t.id},{"path",t.dir.u8string()}});incoming.erase(it);}return;}
 throw std::runtime_error("Unknown campaign message");
}
}
extern "C" {
void campaign_init(const char* game,int host,ID me,ID hostid,Send sender){root=fs::absolute(game).lexically_normal();base=root/"CoopHostSaves";hosting=host!=0;self=me;owner=hostid;sendPacket=sender;ipc=root/(".g2campaign-"+std::to_string(GetCurrentProcessId()));for(const char* suffix:{".ready",".command",".reply",".event"})fs::remove(ipc.string()+suffix);enabled=true;SetEnvironmentVariableA("G2_COOP_CAMPAIGN",ipc.string().c_str());SetEnvironmentVariableA("G2_COOP_CAMPAIGN_HOST",hosting?"1":"0");status("starting");}
void campaign_owner(ID id){owner=id;send(owner,{{"op","hello"}});}
int campaign_registered(ID id){return clients.count(id)?1:0;}
void campaign_prune(int(*member)(ID)){for(auto it=clients.begin();it!=clients.end();)if(!member(*it))it=clients.erase(it);else ++it;}
int campaign_ready(){return !enabled||hosting||joinReady;}
void campaign_receive(ID peer,const void* data,int size){if(!enabled||size<=0||size>32768)return;try{auto b=(const uint8_t*)data;J msg=J::from_bson(b,b+size);if(!hosting&&peer!=owner)return;if(msg.value("op","")=="stored"){std::string id=msg.value("id","");auto item=uploaded.find(id);if(item!=uploaded.end()){cleanCache(item->second);uploaded.erase(item);status("stored",id);}return;}receive(peer,msg);}catch(const std::exception& e){log(std::string("Rejected campaign message: ")+e.what());}}
void campaign_tick(){if(!enabled)return;try{event();nativeReply();transmit();if(joinReady&&!fs::exists(ipc.string()+".ready"))write(ipc.string()+".ready",{{"ready",true}});if(!pending.is_null()&&(LONG)(GetTickCount()-deadline)>0){status("incomplete","Timed out waiting for a player's snapshot; previous complete slot remains valid only for its original host files.");pending=J();incoming.clear();}}catch(const std::exception& e){status("error",e.what());}}
}
