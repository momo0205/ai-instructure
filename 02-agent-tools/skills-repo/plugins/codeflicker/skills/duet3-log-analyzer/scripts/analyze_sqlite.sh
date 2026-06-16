#!/bin/bash
# Duet3 SQLite 数据分析脚本
# 用法: ./analyze_sqlite.sh <sqlite_directory> [workspace_id]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DB_DIR="${1:-.}"
WORKSPACE_ID="${2:-}"

echo -e "${BLUE}=== Duet3 SQLite 数据分析 ===${NC}"
echo "数据库目录: $DB_DIR"
echo ""

# 检查目录是否存在
if [ ! -d "$DB_DIR" ]; then
    echo -e "${RED}错误: 目录不存在: $DB_DIR${NC}"
    exit 1
fi

# 检查是否有 sqlite 文件
SQLITE_FILES=$(find "$DB_DIR" -maxdepth 1 -name "*.sqlite" 2>/dev/null | wc -l)
if [ "$SQLITE_FILES" -eq 0 ]; then
    echo -e "${RED}错误: 目录中没有 .sqlite 文件${NC}"
    exit 1
fi

echo -e "${GREEN}1. 数据库文件列表${NC}"
echo "----------------------------------------"
ls -lah "$DB_DIR"/*.sqlite* 2>/dev/null || echo "无 sqlite 文件"
echo ""

echo -e "${GREEN}2. 各数据库 Key 分布${NC}"
echo "----------------------------------------"

if [ -f "$DB_DIR/session_data.sqlite" ]; then
    echo -e "${YELLOW}>>> session_data.sqlite (旧库)${NC}"
    sqlite3 "$DB_DIR/session_data.sqlite" "
        SELECT 
            CASE 
                WHEN key LIKE 'composerHistory' THEN 'composerHistory'
                WHEN key LIKE 'composerData:%' THEN 'composerData:*'
                ELSE substr(key, 1, 20) || '...'
            END as key_type,
            COUNT(*) as count
        FROM KwaipilotKV 
        GROUP BY key_type
        ORDER BY count DESC
        LIMIT 10;
    " 2>/dev/null || echo "  无法读取或表不存在"
    echo ""
fi

if [ -f "$DB_DIR/index.sqlite" ]; then
    echo -e "${YELLOW}>>> index.sqlite (索引和元数据)${NC}"
    sqlite3 "$DB_DIR/index.sqlite" "
        SELECT 
            CASE 
                WHEN key LIKE 'composerMeta:%' THEN 'composerMeta:*'
                WHEN key LIKE 'composerWorkspaceIndex:%' THEN 'composerWorkspaceIndex:*'
                ELSE substr(key, 1, 25) || '...'
            END as key_type,
            COUNT(*) as count
        FROM KwaipilotKV 
        GROUP BY key_type
        ORDER BY count DESC
        LIMIT 10;
    " 2>/dev/null || echo "  无法读取或表不存在"
    echo ""
fi

if [ -f "$DB_DIR/composer_data.sqlite" ]; then
    echo -e "${YELLOW}>>> composer_data.sqlite (会话消息)${NC}"
    sqlite3 "$DB_DIR/composer_data.sqlite" "
        SELECT 
            CASE 
                WHEN key LIKE 'composerData:%' THEN 'composerData:*'
                ELSE substr(key, 1, 20) || '...'
            END as key_type,
            COUNT(*) as count
        FROM KwaipilotKV 
        GROUP BY key_type
        ORDER BY count DESC
        LIMIT 10;
    " 2>/dev/null || echo "  无法读取或表不存在"
    echo ""
fi

if [ -f "$DB_DIR/api_history.sqlite" ]; then
    echo -e "${YELLOW}>>> api_history.sqlite (API 历史)${NC}"
    sqlite3 "$DB_DIR/api_history.sqlite" "
        SELECT 
            CASE 
                WHEN key LIKE 'apiConversationHistory:%' THEN 'apiConversationHistory:*'
                ELSE substr(key, 1, 20) || '...'
            END as key_type,
            COUNT(*) as count
        FROM KwaipilotKV 
        GROUP BY key_type
        ORDER BY count DESC
        LIMIT 10;
    " 2>/dev/null || echo "  无法读取或表不存在"
    echo ""
fi

if [ -f "$DB_DIR/cache.sqlite" ]; then
    echo -e "${YELLOW}>>> cache.sqlite (缓存)${NC}"
    sqlite3 "$DB_DIR/cache.sqlite" "
        SELECT 
            CASE 
                WHEN key LIKE 'blockCodeCache:%' THEN 'blockCodeCache:*'
                ELSE substr(key, 1, 20) || '...'
            END as key_type,
            COUNT(*) as count
        FROM KwaipilotKV 
        GROUP BY key_type
        ORDER BY count DESC
        LIMIT 10;
    " 2>/dev/null || echo "  无法读取或表不存在"
    echo ""
fi

echo -e "${GREEN}3. 时间线分析${NC}"
echo "----------------------------------------"

if [ -f "$DB_DIR/session_data.sqlite" ]; then
    echo -e "${YELLOW}>>> composerHistory 最近更新时间${NC}"
    sqlite3 "$DB_DIR/session_data.sqlite" "SELECT value FROM KwaipilotKV WHERE key = 'composerHistory';" 2>/dev/null | python3 -c "
import sys, json
from datetime import datetime

try:
    data = json.load(sys.stdin)
    sorted_data = sorted(data, key=lambda x: x.get('lastUpdatedAt', 0), reverse=True)
    
    print(f'总条目数: {len(data)}')
    print('最近更新的 5 条:')
    for item in sorted_data[:5]:
        ts = item.get('lastUpdatedAt', 0)
        dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
        print(f'  {dt} | {item.get(\"sessionId\", \"\")[:20]}... | {item.get(\"name\", \"\")[:30]}')
except Exception as e:
    print(f'  解析失败: {e}')
" 2>/dev/null || echo "  无法解析"
    echo ""
fi

if [ -f "$DB_DIR/index.sqlite" ]; then
    echo -e "${YELLOW}>>> composerMeta 最近更新时间${NC}"
    sqlite3 "$DB_DIR/index.sqlite" "SELECT value FROM KwaipilotKV WHERE key LIKE 'composerMeta:%';" 2>/dev/null | python3 -c "
import sys, json
from datetime import datetime

metas = []
for line in sys.stdin:
    try:
        meta = json.loads(line.strip())
        metas.append(meta)
    except:
        pass

if metas:
    sorted_metas = sorted(metas, key=lambda x: x.get('lastUpdatedAt', 0), reverse=True)
    
    print(f'总条目数: {len(metas)}')
    print('最近更新的 5 条:')
    for meta in sorted_metas[:5]:
        ts = meta.get('lastUpdatedAt', 0)
        dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
        print(f'  {dt} | {meta.get(\"sessionId\", \"\")[:20]}... | {meta.get(\"name\", \"\")[:30]}')
else:
    print('  无 composerMeta 数据')
" 2>/dev/null || echo "  无法解析"
    echo ""
fi

echo -e "${GREEN}4. 数据一致性检查${NC}"
echo "----------------------------------------"

# 检查 composer_data 和 index 的一致性
if [ -f "$DB_DIR/composer_data.sqlite" ] && [ -f "$DB_DIR/index.sqlite" ]; then
    echo -e "${YELLOW}>>> 检查 composer_data 中的会话是否在 index 中有对应的 meta${NC}"
    
    # 获取 composer_data 中的 sessionIds
    COMPOSER_SIDS=$(sqlite3 "$DB_DIR/composer_data.sqlite" "SELECT key FROM KwaipilotKV WHERE key LIKE 'composerData:%';" 2>/dev/null | sed 's/composerData://')
    
    ORPHAN_COUNT=0
    for sid in $COMPOSER_SIDS; do
        META_EXISTS=$(sqlite3 "$DB_DIR/index.sqlite" "SELECT COUNT(*) FROM KwaipilotKV WHERE key = 'composerMeta:$sid';" 2>/dev/null)
        if [ "$META_EXISTS" = "0" ]; then
            echo -e "  ${RED}❌ 孤儿数据: $sid${NC}"
            ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
        fi
    done
    
    if [ "$ORPHAN_COUNT" -eq 0 ]; then
        echo -e "  ${GREEN}✅ 所有 composer_data 都有对应的 composerMeta${NC}"
    else
        echo -e "  ${RED}发现 $ORPHAN_COUNT 个孤儿数据${NC}"
    fi
    echo ""
fi

# 如果提供了工作区 ID，进行针对性分析
if [ -n "$WORKSPACE_ID" ]; then
    echo -e "${GREEN}5. 工作区特定分析: $WORKSPACE_ID${NC}"
    echo "----------------------------------------"
    
    if [ -f "$DB_DIR/session_data.sqlite" ]; then
        echo -e "${YELLOW}>>> 旧库中该工作区的会话${NC}"
        sqlite3 "$DB_DIR/session_data.sqlite" "SELECT value FROM KwaipilotKV WHERE key = 'composerHistory';" 2>/dev/null | python3 -c "
import sys, json
from datetime import datetime

target_ws = '$WORKSPACE_ID'

try:
    data = json.load(sys.stdin)
    matching = [item for item in data if target_ws in item.get('workspaceUri', '')]
    
    print(f'匹配的会话数: {len(matching)}')
    for item in matching[:10]:
        ts = item.get('lastUpdatedAt', 0)
        dt = datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d %H:%M:%S') if ts else 'N/A'
        print(f'  {dt} | {item.get(\"sessionId\", \"\")[:20]}... | {item.get(\"name\", \"\")[:30]}')
except Exception as e:
    print(f'  解析失败: {e}')
" 2>/dev/null || echo "  无法解析"
        echo ""
    fi
    
    if [ -f "$DB_DIR/index.sqlite" ]; then
        echo -e "${YELLOW}>>> 新库中该工作区的索引${NC}"
        sqlite3 "$DB_DIR/index.sqlite" "SELECT key, value FROM KwaipilotKV WHERE key LIKE '%$WORKSPACE_ID%';" 2>/dev/null | head -20
        echo ""
    fi
    
    if [ -f "$DB_DIR/cache.sqlite" ]; then
        echo -e "${YELLOW}>>> cache.sqlite 中该工作区的数据${NC}"
        CACHE_COUNT=$(sqlite3 "$DB_DIR/cache.sqlite" "SELECT COUNT(*) FROM KwaipilotKV WHERE key LIKE '%$WORKSPACE_ID%';" 2>/dev/null || echo "0")
        echo "  匹配的缓存条目数: $CACHE_COUNT"
        echo ""
    fi
fi

echo -e "${GREEN}6. WAL 文件状态${NC}"
echo "----------------------------------------"
for wal in "$DB_DIR"/*.sqlite-wal; do
    if [ -f "$wal" ]; then
        SIZE=$(stat -f%z "$wal" 2>/dev/null || stat -c%s "$wal" 2>/dev/null || echo "unknown")
        if [ "$SIZE" = "0" ]; then
            echo -e "  ${GREEN}$wal: 0 bytes (已 checkpoint)${NC}"
        else
            echo -e "  ${YELLOW}$wal: $SIZE bytes (可能有未提交数据)${NC}"
        fi
    fi
done
echo ""

echo -e "${BLUE}=== 分析完成 ===${NC}"
