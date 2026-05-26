#!/bin/sh
set -eu

npm install --prefer-offline --no-audit
npm run dev
