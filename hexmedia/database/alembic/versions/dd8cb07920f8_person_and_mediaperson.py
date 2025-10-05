"""person and mediaperson

Revision ID: dd8cb07920f8
Revises: b220f98a4489
Create Date: 2025-10-04 18:56:14.440605

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'dd8cb07920f8'
down_revision: Union[str, Sequence[str], None] = 'b220f98a4489'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # 1) New alias + people tables
    op.create_table(
        'person_alias',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('date_created', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=True),
        sa.Column('data_origin', sa.Text(), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alias', sa.String(length=255), nullable=False),
        sa.Column('alias_normalized', sa.String(length=255), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_person_alias')),
        sa.UniqueConstraint('alias_normalized', name='uq_person_alias_normalized_global'),
        schema='hexmedia'
    )
    op.create_table(
        'people',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('date_created', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('clock_timestamp()'), nullable=True),
        sa.Column('data_origin', sa.Text(), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('normalized_name', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('avatar_asset_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['avatar_asset_id'], ['hexmedia.media_asset.id'],
                                name=op.f('fk_people_avatar_asset_id_media_asset'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_people')),
        schema='hexmedia'
    )
    op.create_index('ix_people_display_name_trgm', 'people', ['display_name'],
                    unique=False, schema='hexmedia',
                    postgresql_ops={'display_name': 'gin_trgm_ops'},
                    postgresql_using='gin')
    op.create_index('ix_people_normalized_name', 'people', ['normalized_name'],
                    unique=False, schema='hexmedia')

    # 2) M:M link table between people and aliases
    op.create_table(
        'person_alias_link',
        sa.Column('person_id', sa.UUID(), nullable=False),
        sa.Column('alias_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['alias_id'], ['hexmedia.person_alias.id'],
                                name=op.f('fk_person_alias_link_alias_id_person_alias'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['person_id'], ['hexmedia.people.id'],
                                name=op.f('fk_person_alias_link_person_id_people'), ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('person_id', 'alias_id', name=op.f('pk_person_alias_link')),
        sa.UniqueConstraint('person_id', 'alias_id', name='uq_person_alias_link_person_alias'),
        schema='hexmedia'
    )
    op.create_index('ix_person_alias_link_alias_id', 'person_alias_link', ['alias_id'],
                    unique=False, schema='hexmedia')

    # 3) Switch media_person FK: drop old FK to legacy person, THEN drop legacy table
    op.drop_constraint(op.f('fk_media_person_person_id_person'),
                       'media_person', schema='hexmedia', type_='foreignkey')

    # Now it is safe to drop the old table
    op.drop_table('person', schema='hexmedia')

    # 4) Add dedup/indexes and point FK to new people table
    op.create_index('ix_media_person_media_item_id', 'media_person', ['media_item_id'],
                    unique=False, schema='hexmedia')
    op.create_index('ix_media_person_person_id', 'media_person', ['person_id'],
                    unique=False, schema='hexmedia')
    op.create_unique_constraint('uq_media_person_pair', 'media_person',
                                ['media_item_id', 'person_id'], schema='hexmedia')
    op.create_foreign_key(op.f('fk_media_person_person_id_people'),
                          'media_person', 'people', ['person_id'], ['id'],
                          source_schema='hexmedia', referent_schema='hexmedia',
                          ondelete='CASCADE')

    # 5) Tag/MediaTag indexes (independent)
    op.create_index('ix_media_tag_tag_id', 'media_tag', ['tag_id'], unique=False, schema='hexmedia')
    op.create_index('ix_tag_group_id', 'tag', ['group_id'], unique=False, schema='hexmedia')
    op.create_index('ix_tag_name_lower', 'tag', [sa.literal_column('lower(name)')],
                    unique=False, schema='hexmedia')
    op.create_index('ix_tag_parent_id', 'tag', ['parent_id'], unique=False, schema='hexmedia')



def downgrade() -> None:
    # Drop tag/media indexes added up-migration
    op.drop_index('ix_tag_parent_id', table_name='tag', schema='hexmedia')
    op.drop_index('ix_tag_name_lower', table_name='tag', schema='hexmedia')
    op.drop_index('ix_tag_group_id', table_name='tag', schema='hexmedia')
    op.drop_index('ix_media_tag_tag_id', table_name='media_tag', schema='hexmedia')

    # Remove FK to people and media_person extras
    op.drop_constraint(op.f('fk_media_person_person_id_people'),
                       'media_person', schema='hexmedia', type_='foreignkey')
    op.drop_constraint('uq_media_person_pair', 'media_person', schema='hexmedia', type_='unique')
    op.drop_index('ix_media_person_person_id', table_name='media_person', schema='hexmedia')
    op.drop_index('ix_media_person_media_item_id', table_name='media_person', schema='hexmedia')

    # Recreate legacy person table BEFORE re-adding FK to it
    op.create_table(
        'person',
        sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('date_created', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()')),
        sa.Column('last_updated', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('clock_timestamp()')),
        sa.Column('data_origin', sa.TEXT(), nullable=True),
        sa.Column('meta_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('display_name', sa.VARCHAR(length=255), nullable=False),
        sa.Column('normalized_name', sa.VARCHAR(length=255), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_person')),
        schema='hexmedia'
    )

    # Restore FK pointing to legacy person
    op.create_foreign_key(op.f('fk_media_person_person_id_person'),
                          'media_person', 'person', ['person_id'], ['id'],
                          source_schema='hexmedia', referent_schema='hexmedia',
                          ondelete='CASCADE')

    # Tear down people/aliases
    op.drop_index('ix_person_alias_link_alias_id', table_name='person_alias_link', schema='hexmedia')
    op.drop_table('person_alias_link', schema='hexmedia')

    op.drop_index('ix_people_normalized_name', table_name='people', schema='hexmedia')
    op.drop_index('ix_people_display_name_trgm', table_name='people', schema='hexmedia')
    op.drop_table('people', schema='hexmedia')

    op.drop_table('person_alias', schema='hexmedia')

    op.execute("DROP EXTENSION IF EXISTS pg_trgm;")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")

