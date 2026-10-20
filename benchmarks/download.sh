#!/bin/bash
# Tải BIRD dev và Spider vào data/. Mỗi dataset nằm trong thư mục riêng; không chạy code từ dữ liệu tải về.
set -e
cd "$(dirname "$0")/../data"
if [ ! -d bird ]; then
  mkdir -p bird_zip && curl -L -o bird_zip/dev.zip https://bird-bench.oss-cn-beijing.aliyuncs.com/dev.zip
  mkdir -p bird && unzip -q bird_zip/dev.zip -d bird
  # dev.zip chứa dev_20240627/ ... (có thể lồng thêm dev_databases.zip)
  find bird -name 'dev_databases.zip' -exec sh -c 'unzip -q -o "$1" -d "$(dirname "$1")"' _ {} \;
fi
if [ ! -d spider ]; then
  mkdir -p spider_zip
  curl -L -o spider_zip/spider.zip "https://drive.usercontent.google.com/download?id=1403EGqzIDoHMdQF4c9Bkyl7dZLZ5Wt6J&export=download&confirm=t"
  mkdir -p spider && unzip -q spider_zip/spider.zip -d spider
fi
echo done
