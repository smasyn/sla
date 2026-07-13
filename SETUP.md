# Local development

## Create environment

py -3.11 -m venv .venv311

## Activate

PowerShell

Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

.\.venv311\Scripts\Activate.ps1

## Install dependencies

pip install -r requirements.txt

## AWS

aws configure --profile groovelytics-dev

## Run

$env:AWS_PROFILE="groovelytics-dev"

python app.py