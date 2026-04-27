from PyInstaller.utils.hooks import collect_data_files, collect_submodules

hiddenimports = collect_submodules("card_reader_api")
datas = collect_data_files("card_reader_api.seeds", includes=["*.json", "assets/**/*"])
