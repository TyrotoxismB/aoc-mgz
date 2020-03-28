"""Initial."""

# pylint: disable=invalid-name,no-name-in-module

from construct import (Array, Byte, Embedded, Flag, Float32l, If, Int16ul, Int32sl,
                       Int32ul, Padding, Struct, Tell, this, Bytes, Const, IfThenElse)

from mgz.enums import MyDiplomacyEnum, TheirDiplomacyEnum
from mgz.header.objects import existing_object
from mgz.header.playerstats import player_stats
from mgz.util import Find, GotoObjectsEnd, RepeatUpTo, Version

# Player attributes.
attributes = "attributes"/Struct(
    Array(lambda ctx: ctx._._._.replay.num_players, TheirDiplomacyEnum("their_diplomacy"/Byte)),
    Array(9, MyDiplomacyEnum("my_diplomacy"/Int32sl)),
    "allied_los"/Int32ul,
    "allied_victory"/Flag,
    "player_name_length"/Int16ul,
    "player_name"/Bytes(this.player_name_length - 1),
    Padding(1), # 0x00
    Padding(1), # 0x16
    "num_header_data"/Int32ul,
    Padding(1), # 0x21
    player_stats,
    Padding(1),
    "camera_x"/Float32l,
    "camera_y"/Float32l,
    "end_of_camera"/Tell,
    Embedded(If(this._._._.version != Version.AOK, Struct(
        "num_saved_views"/Int32sl,
        # present in resumed games
        If(lambda ctx: ctx.num_saved_views > 0, Array(
            lambda ctx: ctx.num_saved_views, "saved_view"/Struct(
                "camera_x"/Float32l,
                "camera_y"/Float32l
            )
        )),
    ))),
    "spawn_location"/Struct(
        "x"/Int16ul,
        "y"/Int16ul
    ),
    "culture"/Byte,
    "civilization"/Byte,
    "game_status"/Byte,
    "resigned"/Flag,
    Padding(1),
    "player_color"/Byte,
    Padding(1),
)


def can_parse_objects(ctx):
    """Objects cannot be parsed for all version."""
    if ctx._.restore_time != 0:
        return False
    if ctx._._.version in [Version.USERPATCH14, Version.USERPATCH14RC2, Version.USERPATCH15]:
        return True
    if ctx._._.version == Version.DE and ctx._._.save_version >= 13.06:
        return True
    return False


# Initial state of players, including Gaia.
player = "players"/Struct(
    "type"/Byte,
    "unk"/Byte,
    attributes,
    "end_of_attr"/Tell,
    "start_of_objects"/Find(b'\x0b\x00\x08\x00\x00\x00\x02\x00\x00', None),
    Embedded(IfThenElse(lambda ctx: can_parse_objects(ctx),
        Struct(
            "objects"/RepeatUpTo(b'\x00', existing_object),
            Const(b'\x00\x0b'),
            # Skip Gaia trees for performance reasons
            Embedded(IfThenElse(this._.type != 2,
                Struct(
                    "s_size"/Int32ul,
                    "s_grow"/Int32ul,
                    "sleeping_objects"/RepeatUpTo(b'\x00', existing_object),
                    Const(b'\x00\x0b'),
                    "d_size"/Int32ul,
                    "d_grow"/Int32ul,
                    "doppleganger_objects"/RepeatUpTo(b'\x00', existing_object),
                    Const(b'\x00\x0b')
                ),
                Struct(
                    "sleeping_objects"/Array(0, existing_object),
                    "doppleganger_objects"/Array(0, existing_object)
                )
            ))
        ),
        Struct(
            "objects"/Array(0, existing_object),
            "sleeping_objects"/Array(0, existing_object),
            "doppleganger_objects"/Array(0, existing_object)
        )
    )),
    "end_of_objects"/GotoObjectsEnd()
)


# Initial state.
initial = "initial"/Struct(
    "restore_time"/Int32ul, # zero for non-restored
    "num_particles"/Int32ul,
    "particles"/Bytes(lambda ctx: ctx.num_particles * 27),
    "identifier"/Int32ul,
    Array(lambda ctx: ctx._.replay.num_players, player),
    Padding(21),
)
