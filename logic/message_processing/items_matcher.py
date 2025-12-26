import logging
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def filter_by_grade_and_duration(top5, entry, items_in_db):

    # Filter by grade
    if entry['item_grade'] != 'undefined':
        top5 = [x for x in top5 if x and items_in_db[x["index"]].item_grade == entry['item_grade']]
    elif len(top5) >= 2 and top5[0]["item_name"] == top5[1]["item_name"]:
        logger.warning(f"No unique match found for item: {entry['item_name']}")
        return None

    if not top5:
        logger.warning(f"No match found for: {entry['item_name']}")
        return None

    # Filter by duration
    if entry['item_duration'] != 'undefined':
        top5 = [x for x in top5 if x and items_in_db[x["index"]].item_duration == entry['item_duration']]
    elif len(top5) >= 2 and top5[0]["item_name"] == top5[1]["item_name"]:
        logger.warning(f"No unique duration match for item: {entry['item_name']}")
        return None

    if not top5:
        logger.warning(f"No valid match found for: {entry['item_name']}")
        return None

    best_match = top5[0]
    if best_match["score"] < 80:
        logger.info(f"Low match score ({best_match['score']:.1f}%) — item not inserted: {entry['item_name']}")
        return None
    else:
        return top5[0]


def find_top5_item_matches(items_in_db, entry):
    entry_name = entry['item_name'].lower()
    candidates = []

    for j, db_item in enumerate(items_in_db):
        db_name = db_item.item_name.lower()

        # Считаем score
        ratio_score = fuzz.ratio(entry_name, db_name)
        partial_score = fuzz.partial_ratio(entry_name, db_name)
        current_score = (ratio_score * 0.4 + partial_score * 0.6)

        candidates.append({
            "item_name": db_item.item_name,
            "index": j,
            "score": current_score
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)

    return candidates[:5]