#include<memory>
#include<map>
#include<mutex>
#include<utility>

namespace traffic_manager {

    template <typename K, typename D>
    class BufferMap {

    private:
        std::map<K, D>          data_map;
        std::mutex              put_mutex;

    public:
        BufferMap() {}
        ~BufferMap() {}

        void put(K key, D data) {

            if (key == NULL or data == NULL) {
                throw "Key or Data is Null!";
            }

            if (data_map.find(key) == data_map.end()) {
                std::lock_guard<std::mutex> lock (put_mutex);
                
                if (data_map.find(key) == data_map.end()) {
                    data_map.insert(std::pair<K, D>(key, data));
                }
            }
        }

        D get(K key){
            // std::cout << "In Get before At" << std::endl;
            auto value = data_map.at(key);
            // std::cout << "In Get after At" << std::endl;
            return value;
        }

        bool contains(K key){
            return data_map.find(key) != data_map.end();
        }

    };
}
