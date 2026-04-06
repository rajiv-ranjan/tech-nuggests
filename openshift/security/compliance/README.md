# OpenShift Compliance Operator — user guide

This directory contains manifests and a helper script to install the **OpenShift Compliance Operator**, run **CIS** scans (`ocp4-cis` and `ocp4-cis-node`), and inspect **results** and **remediations**.

Official reference: [OpenShift Container Platform — Security and compliance](https://docs.redhat.com/en/documentation/openshift_container_platform/4.21/html/security_and_compliance/index) (Compliance Operator install, scans, results, and remediations).

---

## Prerequisites

- **`oc`** logged in as a user with **cluster-admin** (or equivalent) rights.
- A **default or configured StorageClass** for persistent raw scan results (see `ScanSetting` `rawResultStorage` in the sample manifest).
- **RHCOS** nodes and consistent OS versions across the cluster (see Red Hat release notes for the Compliance Operator).
- For **Red Hat OpenShift on AWS hosted control planes (ROSA HCP)** or similar, you may need script flags described below so the operator schedules on worker nodes.

---

## Files in this directory

| File | Purpose |
|------|---------|
| [install-run-compliance-operator.sh](install-run-compliance-operator.sh) | Installs the operator, applies scan manifests, waits for scans, prints results and remediations. |
| [scan-setting-bank-mobile-banking-app.yaml](scan-setting-bank-mobile-banking-app.yaml) | `ScanSetting`: schedule, node roles, storage for raw results, timeouts. |
| [scan-setting-binding-cis-compliance.yaml](scan-setting-binding-cis-compliance.yaml) | `ScanSettingBinding`: binds **ocp4-cis** + **ocp4-cis-node** to the `ScanSetting` above. |

Default ComplianceSuite name (from the binding): **`bank-mobile-banking-app-cis-compliance`**.

---

## Quick start (recommended)

From this directory:

```bash
chmod +x install-run-compliance-operator.sh

# Install operator + apply CIS ScanSetting/ScanSettingBinding + wait for install and scan completion
./install-run-compliance-operator.sh all --wait
```

Then show check results and remediations:

```bash
./install-run-compliance-operator.sh results
```

---

## Helper script commands

Run `./install-run-compliance-operator.sh --help` for the full option list. Summary:

| Command | What it does |
|---------|----------------|
| `install` | Creates `Namespace`, `OperatorGroup`, and `Subscription` for the Compliance Operator (OLM). |
| `run` | Applies `scan-setting-bank-mobile-banking-app.yaml` and `scan-setting-binding-cis-compliance.yaml`. |
| `all` | Runs `install` then `run`. |
| `results` | Prints suites, scans, `ComplianceCheckResult` summary, failures, and `ComplianceRemediation` objects (with optional suite filter). |

### Common options

| Option | Used with | Meaning |
|--------|-----------|---------|
| `--wait` | `install`, `run`, or `all` | After **install**: wait until the operator CSV is **Succeeded**. After **run**: wait until the **ComplianceSuite** is **DONE**. With **all**, both waits run in order. |
| `--wait-timeout SEC` | `install`, `all` | Max wait for CSV (default: **600**). |
| `--scan-wait-timeout SEC` | `run`, `all` | Max wait for ComplianceSuite **DONE** (default: **7200**). |
| `--rosa-hcp` | `install`, `all` | Subscription tuned for ROSA HCP (worker `nodeSelector`). |
| `--clear-default-node-selector` | `install`, `all` | Sets `openshift.io/node-selector=""` on the namespace if your cluster uses a global `defaultNodeSelector`. |
| `--suite NAME` | `results` | Filter by `compliance.openshift.io/suite` (defaults to `SUITE_NAME`). |
| `--all-scans` | `results` | List all results in the namespace (no suite label filter). |

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NAMESPACE` | `openshift-compliance` | Project for operator and scans. |
| `CHANNEL` | `stable` | Operator subscription channel. |
| `INSTALL_PLAN_APPROVAL` | `Automatic` | OLM install plan approval. |
| `SCAN_SETTING_YAML` | `scan-setting-bank-mobile-banking-app.yaml` (next to script) | Path to `ScanSetting`. |
| `SCAN_BINDING_YAML` | `scan-setting-binding-cis-compliance.yaml` (next to script) | Path to `ScanSettingBinding`. |
| `SUITE_NAME` | `bank-mobile-banking-app-cis-compliance` | Suite name for **wait** and default **results** filter. |
| `COMPLIANCE_SUITE_LABEL` | (empty; falls back to `SUITE_NAME`) | Override suite label for `results` without `--suite`. |

Example:

```bash
export NAMESPACE=openshift-compliance
export SUITE_NAME=bank-mobile-banking-app-cis-compliance
./install-run-compliance-operator.sh run --wait --scan-wait-timeout 10800
./install-run-compliance-operator.sh results --suite "$SUITE_NAME"
```

---

## Step-by-step workflows

### 1. Install only the Compliance Operator

```bash
./install-run-compliance-operator.sh install --wait
```

Verify:

```bash
oc get csv -n openshift-compliance
oc get deploy -n openshift-compliance
```

### 2. Configure and start CIS scans only

Use this when the operator is already installed:

```bash
./install-run-compliance-operator.sh run --wait
```

This applies the `ScanSetting` and `ScanSettingBinding` that run **ocp4-cis** (platform) and **ocp4-cis-node** (nodes) together.

Watch scans manually:

```bash
oc get compliancescan -w -n openshift-compliance
oc get compliancesuite -n openshift-compliance
```

### 3. Review results and possible remediations

```bash
./install-run-compliance-operator.sh results
```

The script prints suites, scans, failing checks, checks with **automated** remediations, checks that need **manual** review, and remediation objects (including `spec.apply` when columns are supported).

Useful manual commands:

```bash
oc describe compliancecheckresult/<name> -n openshift-compliance
oc describe complianceremediation/<name> -n openshift-compliance
```

To **apply** an automated remediation after review (example pattern):

```bash
oc patch complianceremediation/<name> -n openshift-compliance --type=merge -p '{"spec":{"apply":true}}'
```

Follow Red Hat guidance for your environment before applying remediations in production.

### 4. Manual apply of manifests (without the script)

If you prefer plain `oc`:

```bash
oc apply -f scan-setting-bank-mobile-banking-app.yaml
oc apply -f scan-setting-binding-cis-compliance.yaml
```

Ensure the project exists and the Compliance Operator is installed first.

---

## Support: must-gather

To collect Compliance Operator diagnostics for a support case, use the **must-gather** image from the installed CSV (resolve the version from the cluster instead of hardcoding it):

```bash
OPERATOR_CSV=$(oc get csv -n openshift-compliance -o name | grep compliance-operator | head -1)
oc adm must-gather --image="$(oc get "${OPERATOR_CSV}" -n openshift-compliance -o jsonpath='{.spec.relatedImages[?(@.name=="must-gather")].image}')"
```

If you already know the CSV resource name (for example `csv/compliance-operator.v1.8.2`):

```bash
oc adm must-gather --image="$(oc get csv compliance-operator.v1.8.2 -n openshift-compliance -o jsonpath='{.spec.relatedImages[?(@.name=="must-gather")].image}')"
```

---

## Notes on the sample `ScanSetting`

- **Schedule** `*/30 * * * *` runs scans every 30 minutes. Adjust or set **`suspend: true`** if you want on-demand scans only.
- **Raw results** use a **1Gi** PVC with **ReadWriteOnce**; your platform must support provisioning volumes for the chosen storage class.
- **Platform + node profiles**: the binding uses **ocp4-cis** and **ocp4-cis-node** as recommended by Red Hat for paired platform and node coverage.

---

## Further reading

- [Installing the Compliance Operator using the CLI](https://docs.redhat.com/en/documentation/openshift_container_platform/4.21/html/security_and_compliance/compliance-operator#compliance-operator-install-cli)
- [Managing Compliance Operator result and remediation](https://docs.redhat.com/en/documentation/openshift_container_platform/4.21/html/security_and_compliance/compliance-operator#compliance-results)
