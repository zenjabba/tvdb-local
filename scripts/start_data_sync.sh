#!/bin/bash

echo "=== TVDB Data Sync Tool ==="
echo

# Check if services are running
if ! docker-compose ps | grep -q "Up"; then
    echo "Error: Services are not running. Start them first with: docker-compose up -d"
    exit 1
fi

case "${1:-menu}" in
    static)
        echo "Syncing static data (genres, languages, etc.)..."
        docker-compose exec -T worker python -c "
from app.workers.sync_tasks import sync_static_data
result = sync_static_data.delay()
print(f'Started static data sync - Task ID: {result.id}')
print('Check worker logs for progress: docker-compose logs -f worker')
"
        ;;
    
    series)
        if [ -z "$2" ]; then
            echo "Usage: $0 series <series_id>"
            echo "Example: $0 series 121361  # Game of Thrones"
            exit 1
        fi
        echo "Syncing series $2..."
        docker-compose exec -T worker python -c "
from app.workers.sync_tasks import sync_series_detailed
result = sync_series_detailed.delay($2)
print(f'Started series sync - Task ID: {result.id}')
print('Check worker logs for progress: docker-compose logs -f worker')
"
        ;;
    
    popular)
        echo "Syncing popular series..."
        docker-compose exec -T worker python -c "
from app.workers.sync_tasks import sync_series_detailed
# Popular series IDs
series_data = [
    (121361, 'Game of Thrones'),
    (81189, 'Breaking Bad'),
    (73244, 'The Office (US)'),
    (78901, 'Scrubs'),
    (153021, 'The Mandalorian'),
    (296295, 'Vikings'),
    (361753, 'Stranger Things'),
    (366524, 'The Witcher'),
    (328487, 'The Orville'),
    (273181, 'Sherlock')
]
for series_id, name in series_data:
    result = sync_series_detailed.delay(series_id)
    print(f'Syncing {name} ({series_id}) - Task ID: {result.id}')
print('\\nAll tasks queued. Check worker logs for progress.')
"
        ;;
    
    incremental)
        echo "Running incremental sync (updates from last 7 days)..."
        docker-compose exec -T worker python -c "
from app.workers.sync_tasks import incremental_sync
result = incremental_sync.delay()
print(f'Started incremental sync - Task ID: {result.id}')
print('Check worker logs for progress: docker-compose logs -f worker')
"
        ;;
    
    full)
        echo "WARNING: Full sync will take a long time and use significant API calls."
        read -p "Are you sure you want to continue? (y/N) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "Starting full sync..."
            docker-compose exec -T worker python -c "
from app.workers.sync_tasks import full_sync
result = full_sync.delay()
print(f'Started full sync - Task ID: {result.id}')
print('Check worker logs for progress: docker-compose logs -f worker')
"
        else
            echo "Cancelled."
        fi
        ;;
    
    status)
        echo "Database status:"
        docker-compose exec -T api python -c "
from app.database import SessionLocal
from app.models import Series, Episode, Movie, Genre, Language
from sqlalchemy import func
db = SessionLocal()
print(f'Series count: {db.query(Series).count()}')
print(f'Episodes count: {db.query(Episode).count()}')
print(f'Movies count: {db.query(Movie).count()}')
print(f'Genres count: {db.query(Genre).count()}')
print(f'Languages count: {db.query(Language).count()}')

# Show recent series
recent = db.query(Series).order_by(Series.last_synced.desc()).limit(5).all()
if recent:
    print('\\nRecently synced series:')
    for s in recent:
        print(f'  - {s.name} (ID: {s.tvdb_id})')
db.close()
"
        ;;
    
    search)
        if [ -z "$2" ]; then
            echo "Usage: $0 search <query>"
            echo "Example: $0 search \"breaking bad\""
            exit 1
        fi
        echo "Searching TVDB for: $2"
        docker-compose exec -T api python -c "
import asyncio
from app.services.tvdb_client import tvdb_client

async def search():
    results = await tvdb_client.search_series('$2')
    if results and 'data' in results:
        print(f'Found {len(results[\"data\"])} results:')
        for item in results['data'][:10]:  # Show first 10
            print(f\"  - {item.get('name')} (ID: {item.get('id')}, Year: {item.get('year')})\")
    else:
        print('No results found.')

asyncio.run(search())
"
        ;;
    
    menu|*)
        echo "Usage: $0 <command> [options]"
        echo
        echo "Commands:"
        echo "  static      - Sync static data (genres, languages, etc.)"
        echo "  series <id> - Sync a specific series by TVDB ID"
        echo "  popular     - Sync popular series (pre-defined list)"
        echo "  incremental - Sync recent updates (last 7 days)"
        echo "  full        - Full sync (WARNING: intensive)"
        echo "  status      - Show database statistics"
        echo "  search <q>  - Search TVDB for series"
        echo
        echo "Examples:"
        echo "  $0 static"
        echo "  $0 series 121361    # Sync Game of Thrones"
        echo "  $0 popular          # Sync popular series"
        echo "  $0 search \"doctor who\""
        echo
        echo "Monitor progress:"
        echo "  docker-compose logs -f worker"
        ;;
esac