


from distutils.core import setup
import py2exe

from distutils.filelist import findall
import os
import matplotlib
matplotlibdatadir = matplotlib.get_data_path()
matplotlibdata = findall(matplotlibdatadir)
matplotlibdata_files = []
for f in matplotlibdata:
    dirname = os.path.join('matplotlibdata', f[len(matplotlibdatadir)+1:])
    matplotlibdata_files.append((os.path.split(dirname)[0], [f]))


# why oh why oh why oh why?
# copy C:\Python24\Lib\site-packages\Pmw C:\Python24\Lib\site-packages\Pmw_not
# copy C:\Python24\Lib\site-packages\Pmw\lib C:\Python24\Lib\site-packages\Pmw
# rename them all to remove the "Pmw" from the filenames
# cry and cry and cry.
# cat >  C:\Python24\Lib\site-packages\Pmw\__init__.py
# from Base import *
# from NoteBook import *
# from Color import *
# from ScrolledFrame import *
# from Group import *
# ^D
       
# Edit PIL/__init__.py to import tifimage

# Edit C:\Python24\Lib\site-packages\OpenGL\GL\GL__init__.py
# ... to replace import Numeric with
# import numpy.oldnumeric as Numeric
# #grrr.

setup(
     console = [         
        "../scripts/peaksearch.py",
        "../scripts/fitgrain.py",
        "../scripts/ubi2cellpars.py",
        "../scripts/filtergrain.py",
        "../scripts/filterout.py",
        "../scripts/pars_2_sweeper.py",
        "../scripts/ImageD11_2_shelx.py",
        "../scripts/fit2dcake.py",
        "../scripts/edfheader.py",
        "../scripts/recoveromega.py",
        "../scripts/id11_summarize.py",
        "../scripts/bgmaker.py",
        "../scripts/makemap.py",
        "../scripts/plotedf.py",
        "../scripts/plotgrainhist.py",
        "../scripts/rubber.py",
        "../scripts/edf2bruker.py",
        "../scripts/index_unknown.py",
        "../scripts/ImageD11Server.py",
        "../scripts/powderimagetopeaks.py",
            {  "script" :    "../scripts/ImageD11_gui.py",
        "icon_resources" : [(1, "../docs/multi.ico")] },
        "../ImageD11/plot3d.py",
        # these are from fabian
        "c:/python25/scripts/collapse.py",
        "c:/python25/scripts/median.py",
        "c:/python25/scripts/fabian.py",
        # these are from fabric
        "c:/python25/scripts/plothst.py",
        "c:/python25/scripts/integrate.py",
        "c:/python25/scripts/fabric.py",
        # And this is to filter manually...
        "fable.python.py",
    ]  ,
     options={
             'py2exe': {
                        'excludes' : ['wx'],
                        'includes' : ['OpenGL.GL', 'OpenGL.Tk', 'Pmw'],
                        'packages' : ['matplotlib', 'pytz'],
                        'dll_excludes':['libgdk-win32-2.0-0.dll',
                             'libgobject-2.0-0.dll',
                             'libgdk_pixbuf-2.0-0.dll',
                             'wxmsw26uh_vc.dll']
                       }
            },
     data_files=matplotlibdata_files
)

# Sorry - no idea where the dll excludes come from in the first place
# ... and copy pyopengl directory to your dist directory
print
print "Have you patched your pyopengl and copied togl.dll to dist "
print "eg:"
print "copy OpenGL.__init__.py c:\\python24\\lib\\site-packages\\OpenGl\\__init__.py"
print "copy OpenGL.Tk__init__.py c:\\python24\\lib\\site-packages\\OpenGl\\Tk\\__init__.py"
print "copy c:\\python24\\lib\\site-packages\\OpenGl\\Tk\\win32-tk8.4\\* dist\\"


