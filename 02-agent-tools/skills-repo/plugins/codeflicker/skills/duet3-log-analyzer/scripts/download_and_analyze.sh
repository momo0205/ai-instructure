#!/bin/bash
# Duet3 Log Analyzer - Download and Analyze Script
# Usage: ./download_and_analyze.sh <log-url> [problem-description]

set -e

LOG_URL="$1"
PROBLEM_DESC="$2"
TEMP_DIR=$(mktemp -d "/tmp/duet-logs-XXXXXX")
LOG_DIR="${TEMP_DIR}/extracted_logs"
REPORT_FILE="${TEMP_DIR}/analysis_report.md"
MCP_REPORT="${TEMP_DIR}/mcp_analysis.md"
EXT_REPORT="${TEMP_DIR}/extension_analysis.md"

echo "=== Duet3 Log Analyzer ==="
echo "Temp directory: ${TEMP_DIR}"
if [ -n "$PROBLEM_DESC" ]; then
    echo "Problem: $PROBLEM_DESC"
fi
echo ""

# Download the log archive
echo "[1/5] Downloading log archive..."
ARCHIVE_PATH="${TEMP_DIR}/logs.tar.gz"
if ! curl -fsSL -o "${ARCHIVE_PATH}" "${LOG_URL}"; then
    echo "ERROR: Failed to download log archive"
    rm -rf "${TEMP_DIR}"
    exit 1
fi
echo "      Downloaded successfully"

# Extract logs
echo "[2/5] Extracting logs..."
mkdir -p "${LOG_DIR}"
if ! tar -xzf "${ARCHIVE_PATH}" -C "${LOG_DIR}" 2>/dev/null; then
    # Try zip format
    if ! unzip -o "${ARCHIVE_PATH}" -d "${LOG_DIR}" 2>/dev/null; then
        echo "ERROR: Failed to extract archive"
        rm -rf "${TEMP_DIR}"
        exit 1
    fi
fi

if [ ! -d "${LOG_DIR}" ]; then
    echo "ERROR: Extraction failed"
    rm -rf "${TEMP_DIR}"
    exit 1
fi

FILE_COUNT=$(find "${LOG_DIR}" -type f 2>/dev/null | wc -l)
echo "      Found ${FILE_COUNT} files"

# Find key log files
DUET_LOG=$(find "${LOG_DIR}" -name "duet.log" -type f 2>/dev/null | head -1)
MAIN_LOG=$(find "${LOG_DIR}" -name "main.log" -type f 2>/dev/null | head -1)
MCP_LOGS=$(find "${LOG_DIR}" -type f -name "mcpServer.*.log" 2>/dev/null)
KWAIPILOT_LOGS=$(find "${LOG_DIR}" -type f -name "kwaipilot*.log" 2>/dev/null)
EXTHOST_LOGS=$(find "${LOG_DIR}" -type f -path "*/exthost/*/*.log" 2>/dev/null)
NETWORK_LOGS=$(find "${LOG_DIR}" -type f -name "network*.log" 2>/dev/null)

# Analyze logs
echo "[3/5] Analyzing logs..."

# Initialize main report
cat > "${REPORT_FILE}" << EOF
# Duet3 Log Analysis Report

## Summary

| Metric | Value |
|--------|-------|
| Log Files | ${FILE_COUNT} |
| Analysis Time | $(date) |
EOF
if [ -n "$PROBLEM_DESC" ]; then
    echo "| Problem | ${PROBLEM_DESC} |" >> "${REPORT_FILE}"
fi
echo '|' >> "${REPORT_FILE}"

# ============================================================================
# Critical Issues
# ============================================================================
echo "## Critical Issues" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# MCP Connection Issues
MCP_ERRORS=0
if [ -n "$MCP_LOGS" ]; then
    MCP_ERRORS=$(grep -c -iE 'failed|error|timeout|disconnected' $MCP_LOGS 2>/dev/null || echo 0)
    echo "### MCP Connection Issues: ${MCP_ERRORS}" >> "${REPORT_FILE}"
    if [ "$MCP_ERRORS" -gt 0 ]; then
        echo '```' >> "${REPORT_FILE}"
        grep -iE 'McpServerConnection|errorState|state.*Error' $MCP_LOGS 2>/dev/null | head -20 >> "${REPORT_FILE}"
        echo '```' >> "${REPORT_FILE}"
    fi
    echo "" >> "${REPORT_FILE}"
fi

# Extension Host Issues
EXT_ERRORS=0
if [ -n "$KWAIPILOT_LOGS" ]; then
    EXT_ERRORS=$(grep -c -iE 'crash|exception|fatal|error' $KWAIPILOT_LOGS 2>/dev/null || echo 0)
fi
if [ -n "$MAIN_LOG" ]; then
    EXT_EXIT=$(grep -c -E 'ExtensionHostProcess.*exited|exit\.code' "$MAIN_LOG" 2>/dev/null || echo 0)
fi
echo "### Extension Host Issues: ${EXT_ERRORS} errors, ${EXT_EXIT} exits" >> "${REPORT_FILE}"
if [ "$EXT_ERRORS" -gt 0 ] || [ "$EXT_EXIT" -gt 0 ]; then
    echo '```' >> "${REPORT_FILE}"
    grep -iE 'kwaipilot.*crash|kwaipilot.*exception|ExtensionHostProcess.*exited' $KWAIPILOT_LOGS $MAIN_LOG 2>/dev/null | head -20 >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
fi
echo "" >> "${REPORT_FILE}"

# IPC/Window Communication Issues
IPC_ERRORS=0
if [ -n "$MAIN_LOG" ]; then
    IPC_ERRORS=$(grep -c -E 'MessagePort.*closed|IPC.*error|duet-agent-message.*error' "$MAIN_LOG" 2>/dev/null || echo 0)
fi
echo "### Window/IPC Issues: ${IPC_ERRORS}" >> "${REPORT_FILE}"
if [ "$IPC_ERRORS" -gt 0 ]; then
    echo '```' >> "${REPORT_FILE}"
    grep -E 'MessagePort.*closed|IPC.*error|duet-agent-message' $MAIN_LOG 2>/dev/null | head -20 >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
fi
echo "" >> "${REPORT_FILE}"

# ============================================================================
# Workspace State Comparison
# ============================================================================
echo "## Workspace State Comparison" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

if [ -n "$DUET_LOG" ]; then
    # Count workspaces with missing extensionHostId
    MISSING_EXT=$(grep -oE 'extensionHostId":(null|"[^"]+")' "$DUET_LOG" 2>/dev/null | grep -c "null" || echo 0)
    LOADING_STUCK=$(grep -oE '"loading":true' "$DUET_LOG" 2>/dev/null | wc -l || echo 0)

    echo "**Workspace Status Summary:**" >> "${REPORT_FILE}"
    echo "- Missing extensionHostId: ${MISSING_EXT}" >> "${REPORT_FILE}"
    echo "- Still loading: ${LOADING_STUCK}" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"

    echo "### Workspaces with extensionHostId" >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    grep -oE 'name":"[^"]+".*extensionHostId":"[^"]*"' "$DUET_LOG" 2>/dev/null | sort | uniq >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"

    echo "### Workspaces with loading=true (potential stuck)" >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    grep -oE 'name":"[^"]+".*"loading":true' "$DUET_LOG" 2>/dev/null | sort | uniq >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"

    echo "### Workspaces initialized events received" >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    grep "workspace initialized" "$DUET_LOG" 2>/dev/null | grep -oE 'workspaceId="[^"]+"' | sort | uniq >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"

    echo "### Main process workspace events" >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    grep -E "Sending workspace|workspace initialized" "$MAIN_LOG" 2>/dev/null | head -30 >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}
fi

# ============================================================================
# Network Analysis
# ============================================================================
echo "## Network Analysis" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

if [ -n "$NETWORK_LOGS" ]; then
    NET_ERRORS=$(grep -c -iE 'error|failed|timeout' $NETWORK_LOGS 2>/dev/null || echo 0)
    WS_ERRORS=$(grep -c -iE 'websocket.*error' $NETWORK_LOGS 2>/dev/null || echo 0)
    echo "**Network Issues:** ${NET_ERRORS} - WebSocket: ${WS_ERRORS}" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    echo '### Recent Network Errors' >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    grep -iE 'error|failed|timeout' $NETWORK_LOGS 2>/dev/null | head -20 >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
else
    echo "No network logs found" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
fi

# ============================================================================
# All Error Summary
# ============================================================================
echo "## All Error Summary" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

echo '### Files with Errors' >> "${REPORT_FILE}"
echo '```' >> "${REPORT_FILE}"
find "${LOG_DIR}" -name "*.log" -exec grep -l -iE "error|exception|crash|fatal" {} \; 2>/dev/null | head -20 >> "${REPORT_FILE}"
echo '```' >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

echo '### Error Count by Type' >> "${REPORT_FILE}"
echo '```' >> "${REPORT_FILE}"
for pattern in "mcpServer" "kwaipilot" "main" "duet" "network"; do
    COUNT=$(find "${LOG_DIR}" -type f -name "*${pattern}*.log" -exec grep -c -iE "error|exception|crash" {} \; 2>/dev/null | awk '{s+=$1} END {print s+0}')
    if [ -n "$COUNT" ] && [ "$COUNT" -gt 0 ]; then
        echo "${pattern}.log: ${COUNT} errors" >> "${REPORT_FILE}"
    fi
done
echo '```' >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

# ============================================================================
# Duet Log Errors
# ============================================================================
echo "## Duet Agent Analysis" >> "${REPORT_FILE}"
echo "" >> "${REPORT_FILE}"

if [ -n "$DUET_LOG" ]; then
    DUET_ERRORS=$(grep -c -iE 'error|timeout' "$DUET_LOG" 2>/dev/null || echo 0)
    echo "**Duet Agent Issues:** ${DUET_ERRORS}" >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}"
    echo '### Recent Errors' >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    grep -iE 'error|timeout' "$DUET_LOG" 2>/dev/null | tail -30 >> "${REPORT_FILE}"
    echo '```' >> "${REPORT_FILE}"
    echo "" >> "${REPORT_FILE}
fi

# ============================================================================
# Log Files Found
# ============================================================================
echo "## Log Files Found" >> "${REPORT_FILE}"
echo '```' >> "${REPORT_FILE}"
find "${LOG_DIR}" -type f -name "*.log" | sed "s|${LOG_DIR}/||" | head -50 >> "${REPORT_FILE}"
echo '```' >> "${REPORT_FILE}"

# ============================================================================
# Analysis Complete
# ============================================================================
echo "[4/5] Reports generated!"
echo "[5/5] Cleanup complete!"
echo ""
echo "=== Analysis Complete ==="
echo ""
echo "Reports:"
echo "  - ${REPORT_FILE} (main report)"
if [ -n "$MCP_LOGS" ]; then
    echo "  - ${MCP_REPORT} (MCP details)"
fi
if [ -n "$EXTHOST_LOGS" ] || [ -n "$KWAIPILOT_LOGS" ]; then
    echo "  - ${EXT_REPORT} (extension details)"
fi
echo "  - ${LOG_DIR} (full logs)"
echo ""
echo "To view the report:"
echo "  cat ${REPORT_FILE}"
echo ""
echo "To open in editor:"
echo "  open ${REPORT_FILE}"
