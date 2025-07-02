https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html-single/security_and_compliance/index#configuring-certificates


```bash

openssl s_client -showcerts -connect api.cluster-frnjl.dynamic.redhatworkshops.io:6443 </dev/null | awk '/BEGIN CERT/ {p=1;n++}; p==1 { print > "cert" n ".pem"}; /END CERT/ {p=0};'

```

- Check the dates of expiry

```bash

echo | openssl s_client -connect api.cluster-frnjl.dynamic.redhatworkshops.io:6443 2>/dev/null | openssl x509 -noout -dates

```

oc extract cm/kube-apiserver-server-ca -n openshift-kube-apiserver --to=.

openssl x509 -in ca-bundle.crt -text -noout