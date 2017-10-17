from pprint import pprint
import os
from hurry.filesize import size

dirpath = 'C:\Users\AKANKSHA\Desktop\udacity\openstreet project\sqlite_windows'

files_list = []
for path, dirs, files in os.walk(dirpath):
    files_list.extend([(filename, size(os.path.getsize(os.path.join(path, filename)))) for filename in files])

for filename, size in files_list:
    print '{:.<40s}: {:5s}'.format(filename,size)