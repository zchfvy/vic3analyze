from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
import game_static

class MarketGoods(Base):
    __tablename__ = "market_goods"

    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), primary_key=True)
    game_date: Mapped[datetime] = mapped_column(ForeignKey('samples.game_date'), primary_key=True)
    sample: Mapped["SampleMetadata"] = relationship()
    run: Mapped["RunMetadata"] = relationship()

    good_id: Mapped[str] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(primary_key=True)

    owner_db_id: Mapped[int] = mapped_column(ForeignKey('country_basics.db_id'))
    owner_country: Mapped["CountryBasics"] = relationship()

    buildings_supply: Mapped[int] = mapped_column()
    buildings_demand: Mapped[int] = mapped_column()
    trade_supply: Mapped[int] = mapped_column()
    trade_demand: Mapped[int] = mapped_column()

    # TODO : this is complex to get
    # pops_demand: Mapped[int] = mapped_column()



    @staticmethod
    def collect(replay_data, sample_obj, run_obj):
        ml = replay_data


        goods_data = game_static.get_config_file('common/goods/00_goods.txt')
        goods_lookup = list(goods_data.keys())

        from collections import defaultdict
        mkt_goods = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

        # Capture building production
        for b_id, b in ml['building_manager']['database'].items():
            if isinstance(b, str):
                continue
            goods_in = b.get('input_goods', {}).get('goods',{})
            goods_out = b.get('output_goods', {}).get('goods',{})
            market = ml['states']['database'][b['state']]['market']
            for good, amount in goods_in.items():
                goodname = goods_lookup[good]
                mkt_goods[market][goodname]['bld_demand'] += amount
            for good, amount in goods_out.items():
                goodname = goods_lookup[good]
                mkt_goods[market][goodname]['bld_supply'] += amount

        # Capture trade
        for k, v in ml['trade_route_manager']['database'].items():
            if not isinstance(v, dict):
                continue
            if v['direction'] == 'import':
                mkt_goods[v['source']][v['goods']]['mkt_import'] += v.get('traded',0)
                mkt_goods[v['target']][v['goods']]['mkt_export'] += v.get('traded',0)
            elif v['direction'] == 'export':
                mkt_goods[v['target']][v['goods']]['mkt_import'] += v.get('traded',0)
                mkt_goods[v['source']][v['goods']]['mkt_export'] += v.get('traded',0)


        # TODO: capture pop consumption


        for market, market_data in mkt_goods.items():
            mkt_owner = replay_data['market_manager']['database'][market]['owner']
            for good, good_data in market_data.items():
                yield MarketGoods(
                        sample = sample_obj,
                        run = run_obj,

                        good_id = good,
                        market_id = int(market),
                        owner_db_id = int(mkt_owner),

                        buildings_supply = good_data['bld_supply'],
                        buildings_demand = good_data['bld_demand'],
                        trade_supply = good_data['mkt_import'],
                        trade_demand = good_data['mkt_export']
                        )
