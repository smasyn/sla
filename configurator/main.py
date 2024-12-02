import configparser
import os

class Configurator:
    def __init__(self,fpath):
        if not os.path.isfile(fpath):
            print(f"WARNING config file does not exist: {fpath}")
            return None
        self.configParser   = configparser.RawConfigParser()
        self.configParser.read(fpath)

    def get(self,section,name):
        try:
            return self.configParser.get(section, name)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None
        
    def items(self,section):
        try:
            return self.configParser.items(section)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None
        
    def get_list(self,section,name,sep=','):
        try:
            lst = self.configParser.get(section, name).split(sep)
            lst = map(str.strip, lst)
            return lst
        except (configparser.NoSectionError, configparser.NoOptionError):
            return None
                 
    def get_with_default(self,section, name, default):
        try:
            return self.configParser.get(section, name)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default