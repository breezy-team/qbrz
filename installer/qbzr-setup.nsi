!define PRODUCT_NAME "QBzr"
!define PRODUCT_VERSION "0.9.2"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY "HKLM"

SetCompressor /SOLID lzma
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "qbzr-setup-${PRODUCT_VERSION}.exe"
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
  File "..\*.py" "..\*.txt"
  SetOutPath "$INSTDIR\_ext"
  File "_ext\*.pyd"
  SetOutPath "$INSTDIR\_lib"
  File /r "_lib\*.py"
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
