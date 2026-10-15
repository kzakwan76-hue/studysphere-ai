# Binary search

Binary search finds an item in a sorted list by repeatedly halving the part of the list that could contain it. It compares the target with the middle element. If they are equal, the search is finished. If the target is smaller, the search continues in the left half. If the target is larger, the search continues in the right half.

## Why it is fast

Each comparison removes half of the remaining items, so a list of n items needs at most about log2(n) comparisons. A sorted list of one million items needs at most about 20 comparisons, while a linear search might need one million.

## Requirements

The list must be sorted. If it is not sorted, binary search can miss the target even when it is present.

## Common mistakes

- Computing the middle as (low + high) / 2 can overflow in languages with fixed-size integers.
- Updating low or high without skipping the middle element can cause an infinite loop.
- Forgetting that an empty list must return "not found" immediately.

## Complexity

Time: O(log n). Extra space: O(1) for the iterative version.