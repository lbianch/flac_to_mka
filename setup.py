from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os", "socket", "mutagen", "subprocess", "PIL", "yaml"], 
                     "excludes": ["tkinter"]}

# GUI applications require a different base on Windows (the default is for a
# console application).
# base = "Win32GUI" if sys.platform == "win32" else None

setup(name = "flac_to_mka",
      version = "0.9",
      description = "FLAC to MKA",
      options = {"build_exe": build_exe_options},
      executables = [Executable("flac_to_mka.py"), Executable("flac_rename.py")])