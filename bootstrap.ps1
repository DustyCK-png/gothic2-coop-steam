$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
if(Test-Path vendor/GothicCoop){throw 'vendor/GothicCoop already exists'}
git clone https://github.com/Gothic-Workshop/GothicCoop.git vendor/GothicCoop
if($LASTEXITCODE){throw 'Clone failed'}
git -C vendor/GothicCoop checkout 5af6641aca0707befcfac4d167b0c4c833a09b2f
if($LASTEXITCODE){throw 'Checkout failed'}
git -C vendor/GothicCoop apply ../../patches/GothicCoop.patch
if($LASTEXITCODE){throw 'Patch failed'}
