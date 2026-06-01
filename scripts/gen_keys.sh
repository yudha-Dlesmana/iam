#!/usr/bin/env bash
set -e
KID="${1:-iam-key-1}"
DIR="keys/$KID"
if [ -f "$DIR/private.pem" ]; then
    echo "= keys $KID already exist (skip)"
    exit 0
fi

mkdir -p "$DIR"
openssl genrsa -out "$DIR/private.pem" 2048
openssl rsa -in "$DIR/private.pem" -pubout -out "$DIR/public.pem"
echo "+ generated $DIR"