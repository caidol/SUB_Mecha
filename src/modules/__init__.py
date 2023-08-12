import glob
import sys
from os.path import dirname, basename, isfile
from src import LOAD, NO_LOAD, LOGGER

'''
---------------------------------------------------
    MODULE STRUCTURE EXPLANATION

    /modules/groups/ -> contains all the modules 
    that are used for group related 
    activites (e.g admin)

    /modules/ -> contains all the modules that
    are for utility based features (e.g weather)
---------------------------------------------------
'''

def __generate_module_list():
    # this function will generate a list of all the modules in the modules folder
    # and then will sort them in a manner that allows them to be imported as a whole in the main file

    mods_paths = glob.glob(dirname(__file__) + "/*.py")

    all_modules = [
        basename(f)[:-3]
        for f in mods_paths
        if isfile(f)
        and not f.endswith('__init__.py')
        and not f.endswith('__main__.py')
    ]

    if LOAD or NO_LOAD:
        to_load = LOAD
        
        if to_load:
            if not all(
                any(mod == module for module in all_modules)
                for mod in to_load
            ):
                LOGGER.error("Invalid load order names. Quitting.")
                sys.exit()
            
            all_modules = sorted(set(all_modules) - set(to_load))
            to_load = list(all_modules) + to_load
        else:
            to_load = all_modules  

        if NO_LOAD:
            LOGGER.info("Not loading the module {}".format(NO_LOAD))
            return [item for item in to_load if item not in NO_LOAD]
        
        return to_load
    
    return all_modules
        
ALL_MODULES = sorted(__generate_module_list())
LOGGER.info("Modules to load: %s", str(ALL_MODULES))
__all__ = ALL_MODULES + ["ALL_MODULES"]