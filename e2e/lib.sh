#!/usr/bin/env bash

retry() {
	local COUNT="${1:-10}"
	local SLEEP="${2:-5}"
	local ERROR=$3
	[ -n "$ERROR" ] && ERROR="$ERROR "
	shift 3
	for c in $(seq 1 "$COUNT"); do
		if "$@"; then
			return 0
		else
			printf "%s(attempt %d/%d)\n" "$ERROR" "$c" "$COUNT" | color "$YELLOW" 1>&2
			if [ "$c" != "$COUNT" ]; then
				printf "retrying in %d seconds...\n" "$SLEEP" | color "$YELLOW" 1>&2
				sleep "$SLEEP"
			fi
		fi
	done
	return 1
}

_not() {
	if "$@"; then
		return 1
	fi
	return 0
}
