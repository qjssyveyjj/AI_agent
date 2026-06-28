# 基于 postgres:16-alpine 编译 pgvector 扩展，产出小体积的 alpine 镜像。
# 用 OPTFLAGS="" 跳过 LLVM 位码生成，免装 clang/llvm，构建更稳更快。
ARG PG_BASE=m.daocloud.io/docker.io/library/postgres:16-alpine
ARG PGVECTOR_VERSION=v0.8.0
# 如内网无法访问 github，可在构建时用 --build-arg PGVECTOR_REPO=<镜像地址> 覆盖
ARG PGVECTOR_REPO=https://github.com/pgvector/pgvector.git

FROM ${PG_BASE} AS builder
ARG PGVECTOR_VERSION
ARG PGVECTOR_REPO
RUN apk add --no-cache build-base git \
    && git clone --branch ${PGVECTOR_VERSION} --depth 1 ${PGVECTOR_REPO} /tmp/pgvector \
    && cd /tmp/pgvector \
    && make OPTFLAGS="" \
    && make install

FROM ${PG_BASE}
# 仅拷贝编译产物，最终镜像保持 alpine 精简体积
COPY --from=builder /usr/local/lib/postgresql/vector.so /usr/local/lib/postgresql/
COPY --from=builder /usr/local/share/postgresql/extension/vector* /usr/local/share/postgresql/extension/
