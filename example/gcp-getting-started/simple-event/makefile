export ENV=dev
export GCP_PROJECT=aster-data-platform
export LOG_LEVEL=DEBUG

list-ids:
	@python -c "from src.operator.event import PasteBinOperator; PasteBinOperator().execute(data={'request_type': 'list-ids'}, topic='prod-paste-bin')"
get-content:
# @python -c "from src.operator.event import PasteBinOperator; PasteBinOperator().execute(data={'request_type': 'get-content', 'id': 'vNrgNqbd'}, topic='prod-paste-bin')"
	@python -c "from src.operator.event import PasteBinOperator; PasteBinOperator().execute(data={'request_type': 'get-content', 'id': 'yqNkp3mR'}, topic='prod-paste-bin')"
