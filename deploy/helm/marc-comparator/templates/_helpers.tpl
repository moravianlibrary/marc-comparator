{{/*
Chart name truncated to 63 chars.
*/}}
{{- define "marc-comparator.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Fully qualified app name.
*/}}
{{- define "marc-comparator.fullname" -}}
{{- if contains .Chart.Name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Common labels.
*/}}
{{- define "marc-comparator.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: {{ include "marc-comparator.name" . }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}

{{/*
Selector labels for a specific component.
*/}}
{{- define "marc-comparator.selectorLabels" -}}
app.kubernetes.io/name: {{ include "marc-comparator.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Resolve image reference for a component.
Usage: {{ include "marc-comparator.image" (dict "image" .Values.app.image "global" .Values.image) }}
*/}}
{{- define "marc-comparator.image" -}}
{{- $registry := .global.registry -}}
{{- $repo := .image.repository -}}
{{- $tag := .image.tag | default .global.tag -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repo $tag -}}
{{- else -}}
{{- printf "%s:%s" $repo $tag -}}
{{- end -}}
{{- end }}
