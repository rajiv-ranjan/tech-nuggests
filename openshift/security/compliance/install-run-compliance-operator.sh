#!/bin/bash
#
# install-run-compliance-operator.sh
# Install the OpenShift Compliance Operator (OLM) and/or apply CIS ScanSetting resources.
#
# Install flow based on: OpenShift Container Platform 4.21 — Security and compliance,
#   Chapter 5.5.1.2 "Installing the Compliance Operator using the CLI"
#   https://docs.redhat.com/en/documentation/openshift_container_platform/4.21/pdf/security_and_compliance/OpenShift_Container_Platform-4.21-Security_and_compliance-en-US.pdf
#
# Prerequisites (documentation):
#   - Cluster administrator credentials.
#   - A StorageClass for ComplianceScan raw results (ScanSetting rawResultStorage).
#   - Consistent node OS versions across the cluster.
#
# Usage:
#   ./install-run-compliance-operator.sh install [options]
#   ./install-run-compliance-operator.sh run [options]
#   ./install-run-compliance-operator.sh all [options]
#   ./install-run-compliance-operator.sh results [options]
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

NAMESPACE="${NAMESPACE:-openshift-compliance}"
CHANNEL="${CHANNEL:-stable}"
INSTALL_PLAN_APPROVAL="${INSTALL_PLAN_APPROVAL:-Automatic}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-600}"
SCAN_WAIT_TIMEOUT="${SCAN_WAIT_TIMEOUT:-7200}"

SCAN_SETTING_YAML="${SCAN_SETTING_YAML:-${SCRIPT_DIR}/scan-setting-bank-mobile-banking-app.yaml}"
SCAN_BINDING_YAML="${SCAN_BINDING_YAML:-${SCRIPT_DIR}/scan-setting-binding-cis-compliance.yaml}"
# ComplianceSuite name matches ScanSettingBinding metadata.name in scan-setting-binding-cis-compliance.yaml
SUITE_NAME="${SUITE_NAME:-bank-mobile-banking-app-cis-compliance}"
# Filter results/remediations by suite label (defaults to SUITE_NAME); override with --suite
COMPLIANCE_SUITE_LABEL="${COMPLIANCE_SUITE_LABEL:-}"

ROSA_HCP=false
RESULT_NO_SUITE_FILTER=false
CLEAR_DEFAULT_NODE_SELECTOR=false
WAIT_FLAG=false
WAIT_INSTALL=false
WAIT_SCAN=false

usage() {
    cat <<'USAGE'
install-run-compliance-operator.sh — Install Compliance Operator and/or run CIS ScanSetting

Commands:
  install   Create Namespace, OperatorGroup, Subscription (OLM install).
  run       Apply ScanSetting and ScanSettingBinding YAML (CIS ocp4-cis + ocp4-cis-node).
  all       Run install, then run (same flags apply).
  results   Show ComplianceSuite status, check results, failing rules, and remediations
            (see doc 5.6.5 "Managing Compliance Operator result and remediation").

Options:
  --wait                    install: wait for CSV Succeeded. run: wait for ComplianceSuite DONE.
                            all: wait for both (use with the matching command).
  --wait-timeout SEC        CSV wait timeout (default: 600).
  --scan-wait-timeout SEC   ComplianceSuite wait timeout (default: 7200).
  --rosa-hcp                Use ROSA HCP Subscription (worker nodeSelector; doc 5.5.1.3).
  --clear-default-node-selector
                            Set openshift.io/node-selector="" on the namespace.
  -h, --help                Show this help.

Environment:
  NAMESPACE              openshift-compliance (default)
  CHANNEL, INSTALL_PLAN_APPROVAL
  SCAN_SETTING_YAML      Path to ScanSetting manifest
  SCAN_BINDING_YAML      Path to ScanSettingBinding manifest
  SUITE_NAME             ComplianceSuite to wait on (default matches binding name)

results-only options:
  --suite NAME           Filter by compliance.openshift.io/suite (default: SUITE_NAME)
  --all-scans            Do not filter by suite label (whole namespace)
USAGE
}

cmd_install() {
    echo "Applying Namespace ${NAMESPACE} (pod-security enforce: privileged; cluster-monitoring label)..."
    oc apply -f - <<EOF
apiVersion: v1
kind: Namespace
metadata:
  labels:
    openshift.io/cluster-monitoring: "true"
    pod-security.kubernetes.io/enforce: privileged
  name: ${NAMESPACE}
EOF

    if [[ "${CLEAR_DEFAULT_NODE_SELECTOR}" == true ]]; then
        echo "Patching namespace annotation openshift.io/node-selector=\"\"..."
        oc annotate namespace "${NAMESPACE}" openshift.io/node-selector="" --overwrite
    fi

    echo "Applying OperatorGroup compliance-operator..."
    oc apply -f - <<EOF
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: compliance-operator
  namespace: ${NAMESPACE}
spec:
  targetNamespaces:
    - ${NAMESPACE}
EOF

    if [[ "${ROSA_HCP}" == true ]]; then
        echo "Applying Subscription compliance-operator-sub (ROSA HCP)..."
        oc apply -f - <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: compliance-operator-sub
  namespace: ${NAMESPACE}
spec:
  channel: "${CHANNEL}"
  installPlanApproval: ${INSTALL_PLAN_APPROVAL}
  name: compliance-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  config:
    nodeSelector:
      node-role.kubernetes.io/worker: ""
EOF
    else
        echo "Applying Subscription compliance-operator-sub..."
        oc apply -f - <<EOF
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: compliance-operator-sub
  namespace: ${NAMESPACE}
spec:
  channel: "${CHANNEL}"
  installPlanApproval: ${INSTALL_PLAN_APPROVAL}
  name: compliance-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
EOF
    fi

    if [[ "${WAIT_INSTALL}" == true ]]; then
        echo "Waiting up to ${WAIT_TIMEOUT}s for CSV phase Succeeded in ${NAMESPACE}..."
        oc wait csv -n "${NAMESPACE}" --all \
            --for=jsonpath='{.status.phase}'=Succeeded \
            --timeout="${WAIT_TIMEOUT}s"
    fi

    echo ""
    echo "Verification:"
    echo "  oc get csv -n ${NAMESPACE}"
    echo "  oc get deploy -n ${NAMESPACE}"
    echo ""
    oc get csv -n "${NAMESPACE}" || true
    oc get deploy -n "${NAMESPACE}" || true
}

cmd_run() {
    if [[ ! -f "${SCAN_SETTING_YAML}" ]]; then
        echo "error: ScanSetting file not found: ${SCAN_SETTING_YAML}" >&2
        exit 1
    fi
    if [[ ! -f "${SCAN_BINDING_YAML}" ]]; then
        echo "error: ScanSettingBinding file not found: ${SCAN_BINDING_YAML}" >&2
        exit 1
    fi

    if ! oc get csv -n "${NAMESPACE}" -o jsonpath='{.items[*].status.phase}' 2>/dev/null | grep -q Succeeded; then
        echo "warning: No CSV in Succeeded phase in ${NAMESPACE}. Install the operator first (install command)." >&2
    fi

    echo "Applying ScanSetting from ${SCAN_SETTING_YAML}..."
    oc apply -f "${SCAN_SETTING_YAML}"
    echo "Applying ScanSettingBinding from ${SCAN_BINDING_YAML}..."
    oc apply -f "${SCAN_BINDING_YAML}"

    if [[ "${WAIT_SCAN}" == true ]]; then
        echo "Waiting for ComplianceSuite ${SUITE_NAME} to exist (up to 120s)..."
        local wait_ready=120
        local start=$SECONDS
        while (( SECONDS - start < wait_ready )); do
            if oc get "compliancesuite/${SUITE_NAME}" -n "${NAMESPACE}" &>/dev/null; then
                break
            fi
            sleep 2
        done
        if ! oc get "compliancesuite/${SUITE_NAME}" -n "${NAMESPACE}" &>/dev/null; then
            echo "error: ComplianceSuite ${SUITE_NAME} not found in ${NAMESPACE}. Check ScanSettingBinding and operator logs." >&2
            exit 1
        fi
        echo "Waiting up to ${SCAN_WAIT_TIMEOUT}s for ComplianceSuite ${SUITE_NAME} phase DONE..."
        oc wait "compliancesuite/${SUITE_NAME}" -n "${NAMESPACE}" \
            --for=jsonpath='{.status.phase}'=DONE \
            --timeout="${SCAN_WAIT_TIMEOUT}s"
        echo "ComplianceSuite ${SUITE_NAME} finished (phase DONE)."
    fi

    echo ""
    echo "Follow scan progress:"
    echo "  oc get compliancescan -n ${NAMESPACE} -w"
    echo "  oc get compliancesuite -n ${NAMESPACE}"
    echo ""
    oc get compliancescan -n "${NAMESPACE}" || true
}

cmd_results() {
    local suite="${COMPLIANCE_SUITE_LABEL:-$SUITE_NAME}"
    local suite_sel=()
    if [[ "${RESULT_NO_SUITE_FILTER}" != true ]]; then
        suite_sel=( -l "compliance.openshift.io/suite=${suite}" )
    fi

    echo "=== ComplianceSuites (${NAMESPACE}) ==="
    oc get compliancesuite -n "${NAMESPACE}" || true
    echo ""

    echo "=== ComplianceScans (${NAMESPACE}) ==="
    oc get compliancescan -n "${NAMESPACE}" || true
    echo ""

    if [[ "${RESULT_NO_SUITE_FILTER}" == true ]]; then
        echo "=== ComplianceCheckResults (all in namespace) ==="
        oc get compliancecheckresults -n "${NAMESPACE}" 2>/dev/null || {
            echo "warning: could not list compliancecheckresults (scan finished and CRs present?)." >&2
        }
    else
        echo "=== ComplianceCheckResults (suite=${suite}) ==="
        if ! oc get compliancecheckresults -n "${NAMESPACE}" "${suite_sel[@]}" 2>/dev/null; then
            echo "warning: no results for suite label ${suite}. Try --all-scans or --suite <ComplianceSuite-name>." >&2
            echo "Listing all ComplianceCheckResults in namespace:"
            oc get compliancecheckresults -n "${NAMESPACE}" || true
        fi
    fi
    echo ""

    if [[ "${RESULT_NO_SUITE_FILTER}" == true ]]; then
        echo "=== Failing checks (FAIL) — all ==="
        oc get compliancecheckresults -n "${NAMESPACE}" \
            -l 'compliance.openshift.io/check-status=FAIL' 2>/dev/null || true
    else
        echo "=== Failing checks (FAIL, suite=${suite}) ==="
        oc get compliancecheckresults -n "${NAMESPACE}" \
            -l "compliance.openshift.io/suite=${suite},compliance.openshift.io/check-status=FAIL" 2>/dev/null || true
    fi
    echo ""

    if [[ "${RESULT_NO_SUITE_FILTER}" == true ]]; then
        echo "=== Failing checks with automated remediation available ==="
        oc get compliancecheckresults -n "${NAMESPACE}" \
            -l 'compliance.openshift.io/check-status=FAIL,compliance.openshift.io/automated-remediation' 2>/dev/null || true
        echo ""
        echo "=== Failing checks requiring manual review (no automated remediation) ==="
        oc get compliancecheckresults -n "${NAMESPACE}" \
            -l 'compliance.openshift.io/check-status=FAIL,!compliance.openshift.io/automated-remediation' 2>/dev/null || true
    else
        echo "=== Failing checks with automated remediation (suite=${suite}) ==="
        oc get compliancecheckresults -n "${NAMESPACE}" \
            -l "compliance.openshift.io/suite=${suite},compliance.openshift.io/check-status=FAIL,compliance.openshift.io/automated-remediation" 2>/dev/null || true
        echo ""
        echo "=== Failing checks requiring manual review (suite=${suite}) ==="
        oc get compliancecheckresults -n "${NAMESPACE}" \
            -l "compliance.openshift.io/suite=${suite},compliance.openshift.io/check-status=FAIL,!compliance.openshift.io/automated-remediation" 2>/dev/null || true
    fi
    echo ""

    if [[ "${RESULT_NO_SUITE_FILTER}" == true ]]; then
        echo "=== ComplianceRemediations (all in namespace) ==="
        oc get complianceremediations -n "${NAMESPACE}" 2>/dev/null || true
    else
        echo "=== ComplianceRemediations (suite=${suite}) ==="
        oc get complianceremediations -n "${NAMESPACE}" "${suite_sel[@]}" 2>/dev/null || true
    fi
    echo ""

    echo "=== Remediation apply flag (spec.apply) — same name as ComplianceCheckResult when auto-fix exists ==="
    if [[ "${RESULT_NO_SUITE_FILTER}" == true ]]; then
        oc get complianceremediations -n "${NAMESPACE}" \
            -o custom-columns='NAME:.metadata.name,APPLY:.spec.apply,STATE:.status.applicationState' 2>/dev/null \
            || oc get complianceremediations -n "${NAMESPACE}" -o wide 2>/dev/null || true
    else
        oc get complianceremediations -n "${NAMESPACE}" "${suite_sel[@]}" \
            -o custom-columns='NAME:.metadata.name,APPLY:.spec.apply,STATE:.status.applicationState' 2>/dev/null \
            || oc get complianceremediations -n "${NAMESPACE}" "${suite_sel[@]}" -o wide 2>/dev/null || true
    fi
    echo ""

    cat <<EOF
Next steps (see OpenShift documentation — Managing Compliance Operator result and remediation):
  Describe a check:    oc describe compliancecheckresult/<name> -n ${NAMESPACE}
  Describe a fix:      oc describe complianceremediation/<name> -n ${NAMESPACE}
  Apply a remediation: oc patch complianceremediation/<name> -n ${NAMESPACE} --type=merge -p '{"spec":{"apply":true}}'
EOF
}

if ! command -v oc >/dev/null 2>&1; then
    echo "error: oc not found in PATH" >&2
    exit 1
fi

COMMAND=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        install|run|all|results)
            COMMAND="$1"
            shift
            break
            ;;
        -h|--help) usage; exit 0 ;;
        *) echo "error: missing or unknown command: $1" >&2; usage >&2; exit 1 ;;
    esac
done

while [[ $# -gt 0 ]]; do
    case "$1" in
        --rosa-hcp) ROSA_HCP=true; shift ;;
        --clear-default-node-selector) CLEAR_DEFAULT_NODE_SELECTOR=true; shift ;;
        --wait)
            WAIT_FLAG=true
            shift
            ;;
        --wait-timeout)
            WAIT_TIMEOUT="${2:?}"
            shift 2
            ;;
        --scan-wait-timeout)
            SCAN_WAIT_TIMEOUT="${2:?}"
            shift 2
            ;;
        --suite)
            COMPLIANCE_SUITE_LABEL="${2:?}"
            shift 2
            ;;
        --all-scans)
            RESULT_NO_SUITE_FILTER=true
            shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "${COMMAND}" ]]; then
    echo "error: specify a command: install, run, all, or results" >&2
    usage >&2
    exit 1
fi

if [[ "${WAIT_FLAG}" == true ]]; then
    case "${COMMAND}" in
        install) WAIT_INSTALL=true ;;
        run) WAIT_SCAN=true ;;
        all)
            WAIT_INSTALL=true
            WAIT_SCAN=true
            ;;
        results)
            echo "warning: --wait is ignored for results" >&2
            ;;
    esac
fi

case "${COMMAND}" in
    install) cmd_install ;;
    run) cmd_run ;;
    all)
        cmd_install
        echo ""
        cmd_run
        ;;
    results) cmd_results ;;
esac
