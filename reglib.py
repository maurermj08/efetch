from Registry import Registry
import binascii

def get_registry(pod):
    return Registry.Registry(pod)

def parse_reg(key, depth=0):
    reg_str = '\t'  * depth + key.path() + "\n"
    if depth < 6:
        for subkey in key.subkeys():
            reg_str += parse_reg(subkey, depth + 1)
    return reg_str

def get_values(key_name, pod):
    #for value in [v for v in key.values() if v.value_type() == Registry.RegSZ or v.value_type() == Registry.RegExpandSZ]:
    reg = get_registry(pod)
    results = []
    try:
        key = reg.open(key_name)
        for value in key.values():
            if value.value_type_str() == "RegBin":
                results.append({ 'name': value.name(), 'type': value.value_type_str(), 'value': "0x" + str(binascii.hexlify(value.value())) })
            else:
                results.append({ 'name': value.name(), 'type': value.value_type_str(), 'value': value.value() })
        return results
    except Registry.RegistryKeyNotFoundException:
        print("Error: couldn't find the key: " + key_name)
        return None

def get_subkeys(key_name, reg):
    try:
        subkeys = []
        key = reg.open(key_name)
        for subkey in key.subkeys():
            subkeys.append(subkey.name())
        return subkeys
    except Registry.RegistryKeyNotFoundException:
        print("Error: couldn't find the key: " + key_name)
        return None


