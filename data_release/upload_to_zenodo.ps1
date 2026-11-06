# One-line launcher for zenodo_upload.py (Windows PowerShell 5.1).
# Asks for the Zenodo personal access token with masked input, keeps it only in this process,
# runs the upload (draft + reserved DOI, no publishing) and clears the variable afterwards.
#
#   powershell -ExecutionPolicy Bypass -File E:\DATA\Python\AGB_NE\figures\data_release\upload_to_zenodo.ps1
#   ... upload_to_zenodo.ps1 --deposition 1234567      (resume an existing draft)
#   ... upload_to_zenodo.ps1 --sandbox                 (rehearsal on sandbox.zenodo.org)

$python = "C:\ProgramData\anaconda3\python.exe"
$script = "E:\DATA\Python\AGB_NE\figures\data_release\zenodo_upload.py"
$dir    = "C:\AGB_NE_release"

$secure = Read-Host -AsSecureString "Zenodo personal access token (input is hidden)"
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
$env:ZENODO_TOKEN = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
if (-not $env:ZENODO_TOKEN) { Write-Host "no token entered"; exit 1 }

& $python -X utf8 $script --dir $dir @args
$code = $LASTEXITCODE
Remove-Item Env:ZENODO_TOKEN -ErrorAction SilentlyContinue
exit $code
