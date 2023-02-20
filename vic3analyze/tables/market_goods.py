from datetime import datetime
import logging
from collections import defaultdict

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
import game_static

log = logging.getLogger(__name__)

class MarketGoods(Base):
    __tablename__ = "market_goods"

    run_id: Mapped[int] = mapped_column(ForeignKey('runs.id'), primary_key=True)
    game_date: Mapped[datetime] = mapped_column(ForeignKey('samples.game_date'), primary_key=True)
    sample: Mapped["SampleMetadata"] = relationship()
    run: Mapped["RunMetadata"] = relationship()

    good_id: Mapped[str] = mapped_column(primary_key=True)
    market_id: Mapped[int] = mapped_column(primary_key=True)

    owner_db_id: Mapped[int] = mapped_column(ForeignKey('country_basics.db_id'))
    owner_country: Mapped["CountryBasics"] = relationship(
            primaryjoin="and_("
            "CountryBasics.db_id == MarketGoods.owner_db_id,"
            "CountryBasics.game_date == MarketGoods.game_date,"
            "CountryBasics.run_id == MarketGoods.run_id)",
            foreign_keys=[owner_db_id, game_date, run_id],
            overlaps="sample,run")

    pop_demand: Mapped[int] = mapped_column()
    buildings_supply: Mapped[int] = mapped_column()
    buildings_demand: Mapped[int] = mapped_column()
    trade_supply: Mapped[int] = mapped_column()
    trade_demand: Mapped[int] = mapped_column()

    # TODO : this is complex to get
    # pops_demand: Mapped[int] = mapped_column()

    @staticmethod
    def get_needs_for_pop(pop_obj, state_obj, pop_id, culture_obj):
        state_id = pop_obj['location']
        res = defaultdict(int)

        if pop_obj.get('size_wa', 0) + pop_obj.get('size_dn', 0) == 0:
            return res  # Early exit for size zero pops

        buy_packages = game_static.get_config_file('common/buy_packages/00_buy_packages.txt')
        pop_needs = game_static.get_config_file('common/pop_needs/00_pop_needs.txt')
        defines = game_static.get_config_file('common/defines/00_defines.txt')
        goods_data = game_static.get_config_file('common/goods/00_goods.txt')
        goods_lookup = list(goods_data.keys())
        goods_lookup_rev = {v:k for k, v in enumerate(goods_lookup)}
        pop_needs_lookup = list(pop_needs.keys())
        pop_needs_lookup_rev = {v:k for k, v in enumerate(pop_needs_lookup)}

        obsession_mult = defines['NPops'][0]['OBSESSION_POP_NEED_EXPENSE_MULT']
        taboo_mult = defines['NPops'][0]['TABOO_POP_NEED_EXPENSE_MULT']
        

        try:
            state_needs = state_obj['pop_needs'][str(pop_obj['culture'])]['pop_need_entry_data']
        except KeyError:
            # Some pops will nto have state needs temporarily if they are very
            # new, in tis case the pop only consumes the default good from each
            # need
            state_needs = None
        dependant_consuption = defines['NPops'][0]['DEPENDENT_CONSUMPTION_RATIO']
        effective_consumers = pop_obj.get('size_wa', 0) + pop_obj.get('size_dn', 0)* dependant_consuption
        num_pop_packages = effective_consumers / defines['NPops'][0]['POP_SIZE_PACKAGE']
        buy_package = buy_packages[f"wealth_{pop_obj['wealth']}"]
        for need_id, amount in buy_package['goods'].items():
            need_index = pop_needs_lookup_rev[need_id]
            total_amount = num_pop_packages * amount

            need = pop_needs[need_id]
            if isinstance(need['entry'], list):
                need_good_names = [e['goods'] for e in need['entry']]
            else:
                need_good_names = [need['entry']['goods']]

            # Attenuate for obsessions and taboos
            obsession_factor = 0
            for good_name in need_good_names:
                if good_name in culture_obj.get('obsessions', []):
                    obsession_factor += obsession_mult/len(need_good_names)
                if good_name in culture_obj.get('taboos', []):
                    obsession_factor -= taboo_mult/len(need_good_names)
            total_amount = total_amount * (1+obsession_factor)

            
            if state_needs is None:
                # Special case wehre state has no needs for this pop
                base_units_bought = total_amount
                base_price = goods_data[good_name]['cost']
                units_bought = base_units_bought / base_price
                default_good = need['default']
                default_good_id = goods_lookup_rev[default_good]
                res[default_good_id] += units_bought
                continue

            total_weight = sum(state_needs[need_index]['weights'].values())
            for good_name in need_good_names:
                good_id = goods_lookup_rev[good_name]
                weight = state_needs[need_index]['weights'][str(good_id)]
                pct = 0 if weight == 0 else weight/total_weight
                base_units_bought = pct * total_amount
                base_price = goods_data[good_name]['cost']
                units_bought = base_units_bought / base_price
                res[good_id] += units_bought

        # TODO : get the factor below dynamicly for each pop type
        if pop_obj['type'] == 'peasant':
            for r in res:
                # TODO - get the factor below from defines
                r = r * 0.1  # peasants cosnume 1/10th

        return res



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
            try:
                market = ml['states']['database'][str(b['state'])]['market']
            except KeyError:
                log.error(f"State ID {b['state']} missing from states table!")
            else:
                for good, amount in goods_in.items():
                    goodname = goods_lookup[int(good)]
                    mkt_goods[market][goodname]['bld_demand'] += amount
                for good, amount in goods_out.items():
                    goodname = goods_lookup[int(good)]
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


        for pop_id, pop in ml['pops']['database'].items():
            if pop == 'none':
                continue
            state = ml['states']['database'][str(pop['location'])]
            culture = ml['cultures']['database'][str(pop['culture'])]
            needs = MarketGoods.get_needs_for_pop(pop, state, pop_id, culture)
            for good_id, amount in needs.items():
                goodname = goods_lookup[good_id]
                mkt_goods[state['market']][goodname]['pop_demand'] += amount

        for market, market_data in mkt_goods.items():
            if not isinstance(market, int):
                if market == "none":
                    continue
                log.error("Unknown value for market!")
                continue
            mkt_owner = replay_data['market_manager']['database'][str(market)]['owner']
            for good, good_data in market_data.items():
                yield MarketGoods(
                        sample = sample_obj,
                        run = run_obj,

                        good_id = good,
                        market_id = int(market),
                        owner_db_id = int(mkt_owner),

                        pop_demand = good_data['pop_demand'],
                        buildings_supply = good_data['bld_supply'],
                        buildings_demand = good_data['bld_demand'],
                        trade_supply = good_data['mkt_import'],
                        trade_demand = good_data['mkt_export']
                        )
