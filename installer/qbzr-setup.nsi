!define PRODUCT_NAME "QBzr"
!define PRODUCT_VERSION "0.9.5"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor /SOLID lzma
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "..\qbzr-setup-${PRODUCT_VERSION}.exe"
ShowInstDetails show
ShowUnInstDetails show

; The default installation directory
InstallDir "$APPDATA\bazaar\2.0\plugins\qbzr"

; The default installation directory
InstallDirRegKey HKLM "Software\QBzr\${PRODUCT_NAME}" "InstallDir"

!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING

; Welcome page
!define MUI_WELCOMEPAGE_TITLE_3LINES
!insertmacro MUI_PAGE_WELCOME

; Directory page
!insertmacro MUI_PAGE_DIRECTORY

; Instfiles page
!insertmacro MUI_PAGE_INSTFILES

; Finish page
!define MUI_FINISHPAGE_TITLE_3LINES
!insertmacro MUI_PAGE_FINISH

; Uninstaller pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!define MUI_UNPAGE_FINISH_TITLE_3LINES
!insertmacro MUI_UNPAGE_FINISH

; Language files
!insertmacro MUI_LANGUAGE "English"

; Install
Section "MainSection" SEC01

  ; Files
  SetOutPath "$INSTDIR"
  File "..\__init__.py" "..\*.txt"
  ; Delete files that were moved between 0.9.1 and 0.9.2
  Delete "setup.py"
  Delete "annotate.py"
  Delete "browse.py"
  Delete "cat.py"
  Delete "commit.py"
  Delete "config.py"
  Delete "diff.py"
  Delete "diffview.py"
  Delete "i18n.py"
  Delete "log.py"
  Delete "main.py"
  Delete "pull.py"
  Delete "resources.py"
  Delete "statuscache.py"
  Delete "test.py"
  Delete "ui_bookmark.py"
  Delete "ui_branch.py"
  Delete "ui_pull.py"
  Delete "ui_push.py"
  Delete "util.py"
  RMDir /r "_ext"
  SetOutPath "$INSTDIR\lib"
  File /r "..\lib\*.py"
  SetOutPath "$INSTDIR\_lib"
  File /r "_lib\*.py" "_lib\*.pyd" "_lib\*.dll"
  SetOutPath "$INSTDIR\locale"
  File /r "..\locale\*.mo"

  ; Write the installation path into the registry
  WriteRegStr HKLM "Software\QBzr\${PRODUCT_NAME}" "InstallDir" "$INSTDIR"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninst.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "$(^Name)"
  ;WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayIcon" "$INSTDIR\picard.exe"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
  WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"

SectionEnd

; Uninstall
Section Uninstall

  RMDir /r "$INSTDIR"

  DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
  DeleteRegKey HKLM "Software\QBzr\${PRODUCT_NAME}"
  
SectionEnd
