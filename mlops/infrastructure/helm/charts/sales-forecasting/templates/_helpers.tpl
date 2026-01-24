{{/*
Expand the name of the chart.
*/}}
{{- define "sales-forecasting.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "sales-forecasting.fullname" -}}
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
{{- define "sales-forecasting.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "sales-forecasting.labels" -}}
helm.sh/chart: {{ include "sales-forecasting.chart" . }}
{{ include "sales-forecasting.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "sales-forecasting.selectorLabels" -}}
app.kubernetes.io/name: {{ include "sales-forecasting.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "sales-forecasting.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "sales-forecasting.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
Database connection string
*/}}
{{- define "sales-forecasting.databaseUrl" -}}
{{- if .Values.postgresql.enabled }}
postgresql://postgres:{{ .Values.postgresql.auth.postgresPassword }}@{{ include "sales-forecasting.fullname" . }}-postgresql:5432/{{ .Values.postgresql.auth.database }}
{{- else }}
postgresql://{{ .Values.externalDatabase.username }}:$(POSTGRES_PASSWORD)@{{ .Values.externalDatabase.host }}:{{ .Values.externalDatabase.port }}/{{ .Values.externalDatabase.database }}
{{- end }}
{{- end }}

{{/*
Redis connection string
*/}}
{{- define "sales-forecasting.redisUrl" -}}
{{- if .Values.redis.enabled }}
redis://:{{ .Values.redis.auth.password }}@{{ include "sales-forecasting.fullname" . }}-redis-master:6379/0
{{- else }}
redis://{{ .Values.externalRedis.host }}:{{ .Values.externalRedis.port }}/0
{{- end }}
{{- end }}

{{/*
Celery worker name
*/}}
{{- define "sales-forecasting.celeryWorkerName" -}}
{{ include "sales-forecasting.fullname" . }}-celery-worker
{{- end }}

{{/*
Celery beat name
*/}}
{{- define "sales-forecasting.celeryBeatName" -}}
{{ include "sales-forecasting.fullname" . }}-celery-beat
{{- end }}
