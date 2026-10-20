#include <nlohmann/json.hpp>
#include <fstream>
#include <string>
#include <windows.h>
extern "C" int configure_game_json(const char* root, int port) {
    try {
        if(port<1 || port>65535) return 0;
        std::string path=std::string(root)+"\\system\\GothicCoopConfig.json";
        std::ifstream input(path);
        auto config=nlohmann::json::parse(input);
        input.close();
        if(!config.is_object()) return 0;
        std::string backup=path+".before-steam", temp=path+".steam-tmp";
        if(GetFileAttributesA(backup.c_str())==INVALID_FILE_ATTRIBUTES && !CopyFileA(path.c_str(),backup.c_str(),TRUE))return 0;
        config["server"]="127.0.0.1";
        config["port"]=port;
        config["loopbackOnly"]=true;
        std::ofstream output(temp); output<<config.dump(2)<<"\n";output.close();
        if(!output)return 0;
        return MoveFileExA(temp.c_str(),path.c_str(),MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)!=0;
    } catch(...) {return 0;}
}
