#! /bin/bash

# Upload psql's backup using devagent-listener's .env file
# Usage: bash postgres_upoload_backup.sh ENV_FILE_PATH

set -e
set -u
set -o pipefail

readonly ENV_FILE="${1:?}"

set -a
# shellcheck source=/dev/null
source "${ENV_FILE}"
set +a

BCK_FILE="bck-$(date "+%y-%m-%d-%s").sql"
readonly BCK_FILE

docker exec -it devagent_listener_postgres pg_dumpall -p "${DB_PORT}" -U "${DB_USER}" -l "${DB_DB}" > "${BCK_FILE}"
curl --user "${NEXUS_USERNAME}":"${NEXUS_PASSWORD}" -X PUT "${NEXUS_REPO_URL}/${BCK_FILE}" -T "${BCK_FILE}"
rm "${BCK_FILE}"
