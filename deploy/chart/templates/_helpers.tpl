{{/*
Expand the name of the chart.
*/}}
{{- define "skyops.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "skyops.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "skyops.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "skyops.labels" -}}
helm.sh/chart: {{ include "skyops.chart" . }}
{{ include "skyops.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "skyops.selectorLabels" -}}
app.kubernetes.io/name: {{ include "skyops.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "skyops.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "skyops.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Secret name helper
*/}}
{{- define "skyops.secretName" -}}
{{- if .Values.existingSecret }}
{{- .Values.existingSecret }}
{{- else }}
{{- printf "%s-secrets" (include "skyops.fullname" .) }}
{{- end }}
{{- end }}

{{/*
PostgreSQL fullname helper
*/}}
{{- define "skyops.postgresql.fullname" -}}
{{- printf "%s-postgresql" (include "skyops.fullname" .) }}
{{- end }}

{{/*
PostgreSQL host helper
*/}}
{{- define "skyops.postgresql.host" -}}
{{- if .Values.postgresql.host }}
{{- .Values.postgresql.host }}
{{- else }}
{{- include "skyops.postgresql.fullname" . }}
{{- end }}
{{- end }}

{{/*
PostgreSQL password helper
*/}}
{{- define "skyops.postgresPassword" -}}
{{- if .Values.postgresql.auth.password -}}
{{- .Values.postgresql.auth.password -}}
{{- else -}}
{{- $secretName := include "skyops.secretName" . -}}
{{- $secret := (lookup "v1" "Secret" .Release.Namespace $secretName) -}}
{{- if and $secret (hasKey $secret "data") (hasKey $secret.data "POSTGRES_PASSWORD") -}}
{{- index $secret.data "POSTGRES_PASSWORD" | b64dec -}}
{{- end -}}
{{- end -}}
{{- end }}

{{/*
Database URL helper
*/}}
{{- define "skyops.databaseUrl" -}}
{{- if .Values.externalDatabase.url }}
{{- .Values.externalDatabase.url }}
{{- else }}
{{- printf "postgresql://%s:%s@%s:5432/%s" (default "skyops" .Values.postgresql.auth.username) (include "skyops.postgresPassword" .) (include "skyops.postgresql.host" .) (default "skyops" .Values.postgresql.auth.database) }}
{{- end }}
{{- end }}
