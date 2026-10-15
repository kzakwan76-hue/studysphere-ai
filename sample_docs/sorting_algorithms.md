# Sorting algorithms

Sorting puts items in order, usually from smallest to largest. Choosing an algorithm depends on the size of the data, whether it is already nearly sorted, and how much extra memory is available.

## Bubble sort

Bubble sort repeatedly steps through the list and swaps neighbouring items that are in the wrong order. After each pass the largest remaining item has moved to its final position. It takes O(n squared) time in the worst case, so it is only suitable for teaching and very small lists.

## Merge sort

Merge sort splits the list in half, sorts each half recursively, and merges the two sorted halves. It takes O(n log n) time in every case but needs O(n) extra space for merging. It is stable, which means equal items keep their original order.

## Quick sort

Quick sort picks a pivot, moves smaller items before it and larger items after it, and then sorts both sides recursively. It is fast in practice and sorts in place, but a poor pivot choice gives O(n squared) time in the worst case.

## Stability

A sorting algorithm is stable if items with equal keys stay in the same relative order after sorting. Stability matters when sorting by one field after sorting by another.