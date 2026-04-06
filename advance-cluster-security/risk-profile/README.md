# Risk profile demos — demo applications

To demonstrate different security features, this workflow uses sample applications from the public repository **[mfosterrox/demo-apps](https://github.com/mfosterrox/demo-apps)** (Kubernetes manifests, pipelines, and related assets).

## Deploy manifests

Clone the repository, point `TUTORIAL_HOME` at the local `demo-apps` directory, apply the recursive Kubernetes manifests, then verify **roadshow** demo deployments across the cluster:

```bash
git clone https://github.com/mfosterrox/demo-apps.git
export TUTORIAL_HOME="$(pwd)/demo-apps"
oc apply -f "$TUTORIAL_HOME/kubernetes-manifests/" --recursive
oc get deployments -l demo=roadshow -A
```

## Reference

- Upstream repo: [https://github.com/mfosterrox/demo-apps](https://github.com/mfosterrox/demo-apps)
