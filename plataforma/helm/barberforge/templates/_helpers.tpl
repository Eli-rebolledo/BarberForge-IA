{{/* Nombre base de todos los recursos: el nombre del release (p. ej. «barberforge»). */}}
{{- define "bf.nombre" -}}
{{- .Release.Name | trunc 40 | trimSuffix "-" -}}
{{- end -}}

{{/* Etiquetas comunes (recomendadas por Kubernetes). */}}
{{- define "bf.etiquetas" -}}
app.kubernetes.io/name: barberforge
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: barberforge
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
barberforge/entorno: {{ .Values.entorno }}
{{- end -}}

{{/* Selector de un componente: uso → include "bf.selector" (dict "ctx" . "componente" "api") */}}
{{- define "bf.selector" -}}
app.kubernetes.io/name: barberforge
app.kubernetes.io/instance: {{ .ctx.Release.Name }}
app.kubernetes.io/component: {{ .componente }}
{{- end -}}

{{- define "bf.imagenApi" -}}
{{ .Values.imagenes.api.repositorio }}:{{ .Values.imagenes.api.tag }}
{{- end -}}

{{- define "bf.imagenWeb" -}}
{{ .Values.imagenes.web.repositorio }}:{{ .Values.imagenes.web.tag }}
{{- end -}}

{{/* Seguridad del pod: nunca como root, perfil seccomp por defecto. */}}
{{- define "bf.seguridadPod" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{/* Seguridad del contenedor: sin escalar privilegios, sin capacidades extra, disco de solo lectura. */}}
{{- define "bf.seguridadContenedor" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end -}}

{{/* Variables de entorno de la API, el worker y el Job de migraciones. */}}
{{- define "bf.entornoApi" -}}
envFrom:
  - configMapRef:
      name: {{ include "bf.nombre" . }}-config
env:
  - name: DB_PASSWORD
    valueFrom: {secretKeyRef: {name: {{ .Values.secretos.nombre }}, key: DB_PASSWORD}}
  - name: JWT_SECRET
    valueFrom: {secretKeyRef: {name: {{ .Values.secretos.nombre }}, key: JWT_SECRET}}
  - name: ADMIN_EMAIL
    valueFrom: {secretKeyRef: {name: {{ .Values.secretos.nombre }}, key: ADMIN_EMAIL, optional: true}}
  - name: ADMIN_PASSWORD
    valueFrom: {secretKeyRef: {name: {{ .Values.secretos.nombre }}, key: ADMIN_PASSWORD, optional: true}}
{{- end -}}

{{- define "bf.pullSecrets" -}}
{{- with .Values.imagenes.pullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}
