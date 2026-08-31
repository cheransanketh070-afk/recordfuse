# Releasing

1. Ensure `CHANGELOG.md` documents the release.
2. Update `recordfuse.__version__` and `[project].version` together.
3. Run `make quality` and `python -m build` locally.
4. Tag `vX.Y.Z` from a clean `main` branch.
5. GitHub Actions builds artifacts and verifies installation before publication.
6. Publish to PyPI after configuring trusted publishing for the final GitHub repository.
