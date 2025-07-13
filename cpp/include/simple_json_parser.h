#pragma once

#include <string>
#include <map>
#include <vector>
#include <sstream>
#include <stdexcept>

class SimpleJsonParser {
public:
    class JsonValue {
    public:
        enum Type { STRING, NUMBER, BOOL, OBJECT, ARRAY, NULL_TYPE };
        
        Type type;
        std::string stringValue;
        double numberValue;
        bool boolValue;
        std::map<std::string, JsonValue> objectValue;
        std::vector<JsonValue> arrayValue;
        
        JsonValue() : type(NULL_TYPE), numberValue(0.0), boolValue(false) {}
        JsonValue(const std::string& s) : type(STRING), stringValue(s), numberValue(0.0), boolValue(false) {}
        JsonValue(double n) : type(NUMBER), numberValue(n), boolValue(false) {}
        JsonValue(bool b) : type(BOOL), numberValue(0.0), boolValue(b) {}
        
        // Access methods
        const std::string& asString() const {
            if (type != STRING) throw std::runtime_error("Not a string value");
            return stringValue;
        }
        
        double asDouble() const {
            if (type != NUMBER) throw std::runtime_error("Not a number value");
            return numberValue;
        }
        
        int asInt() const {
            if (type != NUMBER) throw std::runtime_error("Not a number value");
            return static_cast<int>(numberValue);
        }
        
        bool asBool() const {
            if (type != BOOL) throw std::runtime_error("Not a boolean value");
            return boolValue;
        }
        
        const JsonValue& operator[](const std::string& key) const {
            if (type != OBJECT) throw std::runtime_error("Not an object");
            auto it = objectValue.find(key);
            if (it == objectValue.end()) throw std::runtime_error("Key not found: " + key);
            return it->second;
        }
        
        bool contains(const std::string& key) const {
            if (type != OBJECT) return false;
            return objectValue.find(key) != objectValue.end();
        }
        
        size_t size() const {
            if (type == ARRAY) return arrayValue.size();
            if (type == OBJECT) return objectValue.size();
            return 0;
        }
        
        const JsonValue& operator[](size_t index) const {
            if (type != ARRAY) throw std::runtime_error("Not an array");
            if (index >= arrayValue.size()) throw std::runtime_error("Array index out of bounds");
            return arrayValue[index];
        }
    };
    
    static JsonValue parse(const std::string& jsonStr) {
        size_t pos = 0;
        return parseValue(jsonStr, pos);
    }
    
private:
    static void skipWhitespace(const std::string& str, size_t& pos) {
        while (pos < str.length() && (str[pos] == ' ' || str[pos] == '\t' || str[pos] == '\n' || str[pos] == '\r')) {
            pos++;
        }
    }
    
    static JsonValue parseValue(const std::string& str, size_t& pos) {
        skipWhitespace(str, pos);
        
        if (pos >= str.length()) throw std::runtime_error("Unexpected end of input");
        
        char c = str[pos];
        
        if (c == '"') return parseString(str, pos);
        if (c == '{') return parseObject(str, pos);
        if (c == '[') return parseArray(str, pos);
        if (c == 't' && str.substr(pos, 4) == "true") {
            pos += 4;
            return JsonValue(true);
        }
        if (c == 'f' && str.substr(pos, 5) == "false") {
            pos += 5;
            return JsonValue(false);
        }
        if (c == 'n' && str.substr(pos, 4) == "null") {
            pos += 4;
            return JsonValue();
        }
        if (c == '-' || (c >= '0' && c <= '9')) return parseNumber(str, pos);
        
        throw std::runtime_error("Unexpected character: " + std::string(1, c));
    }
    
    static JsonValue parseString(const std::string& str, size_t& pos) {
        if (str[pos] != '"') throw std::runtime_error("Expected '\"'");
        pos++;
        
        std::string result;
        while (pos < str.length() && str[pos] != '"') {
            if (str[pos] == '\\') {
                pos++;
                if (pos >= str.length()) throw std::runtime_error("Unexpected end of input");
                char c = str[pos];
                if (c == '"' || c == '\\' || c == '/') result += c;
                else if (c == 'b') result += '\b';
                else if (c == 'f') result += '\f';
                else if (c == 'n') result += '\n';
                else if (c == 'r') result += '\r';
                else if (c == 't') result += '\t';
                else throw std::runtime_error("Invalid escape sequence");
            } else {
                result += str[pos];
            }
            pos++;
        }
        
        if (pos >= str.length() || str[pos] != '"') throw std::runtime_error("Unterminated string");
        pos++;
        
        return JsonValue(result);
    }
    
    static JsonValue parseNumber(const std::string& str, size_t& pos) {
        size_t start = pos;
        
        if (str[pos] == '-') pos++;
        
        while (pos < str.length() && str[pos] >= '0' && str[pos] <= '9') pos++;
        
        if (pos < str.length() && str[pos] == '.') {
            pos++;
            while (pos < str.length() && str[pos] >= '0' && str[pos] <= '9') pos++;
        }
        
        if (pos < str.length() && (str[pos] == 'e' || str[pos] == 'E')) {
            pos++;
            if (pos < str.length() && (str[pos] == '+' || str[pos] == '-')) pos++;
            while (pos < str.length() && str[pos] >= '0' && str[pos] <= '9') pos++;
        }
        
        std::string numStr = str.substr(start, pos - start);
        return JsonValue(std::stod(numStr));
    }
    
    static JsonValue parseObject(const std::string& str, size_t& pos) {
        if (str[pos] != '{') throw std::runtime_error("Expected '{'");
        pos++;
        
        JsonValue result;
        result.type = JsonValue::OBJECT;
        
        skipWhitespace(str, pos);
        
        if (pos < str.length() && str[pos] == '}') {
            pos++;
            return result;
        }
        
        while (true) {
            skipWhitespace(str, pos);
            
            if (str[pos] != '"') throw std::runtime_error("Expected '\"' for object key");
            JsonValue key = parseString(str, pos);
            
            skipWhitespace(str, pos);
            
            if (pos >= str.length() || str[pos] != ':') throw std::runtime_error("Expected ':'");
            pos++;
            
            JsonValue value = parseValue(str, pos);
            result.objectValue[key.asString()] = value;
            
            skipWhitespace(str, pos);
            
            if (pos >= str.length()) throw std::runtime_error("Unexpected end of input");
            
            if (str[pos] == '}') {
                pos++;
                break;
            }
            
            if (str[pos] != ',') throw std::runtime_error("Expected ',' or '}'");
            pos++;
        }
        
        return result;
    }
    
    static JsonValue parseArray(const std::string& str, size_t& pos) {
        if (str[pos] != '[') throw std::runtime_error("Expected '['");
        pos++;
        
        JsonValue result;
        result.type = JsonValue::ARRAY;
        
        skipWhitespace(str, pos);
        
        if (pos < str.length() && str[pos] == ']') {
            pos++;
            return result;
        }
        
        while (true) {
            JsonValue value = parseValue(str, pos);
            result.arrayValue.push_back(value);
            
            skipWhitespace(str, pos);
            
            if (pos >= str.length()) throw std::runtime_error("Unexpected end of input");
            
            if (str[pos] == ']') {
                pos++;
                break;
            }
            
            if (str[pos] != ',') throw std::runtime_error("Expected ',' or ']'");
            pos++;
        }
        
        return result;
    }
}; 