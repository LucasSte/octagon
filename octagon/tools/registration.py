import octagon.tools.analysis.metadata
import octagon.tools.assets.metadata
import octagon.tools.market_data.metadata
import octagon.tools.utilities.metadata
from octagon.tools.assets.portfolio import Portfolio


def create_tools_list() -> list:
    return (
        octagon.tools.analysis.metadata.DESCRIPTION_LIST
        + octagon.tools.assets.metadata.DESCRIPTION_LIST
        + octagon.tools.market_data.metadata.DESCRIPTION_LIST
        + octagon.tools.utilities.metadata.DESCRIPTION_LIST
    )


def create_dispatch_dictionary(portfolio: Portfolio):
    return (
        Portfolio.build_dispatch_dict(portfolio)
        | octagon.tools.analysis.metadata.DISPATCH_DICT
        | octagon.tools.assets.metadata.DISPATCH_DICT
        | octagon.tools.market_data.metadata.DISPATCH_DICT
        | octagon.tools.utilities.metadata.DISPATCH_DICT
    )
