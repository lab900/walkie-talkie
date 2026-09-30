#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

/// Runs `block` and answers the Objective-C exception it raised, as an `NSError`
/// (domain `NSException`, the exception's name as `NSLocalizedFailureReasonErrorKey`,
/// its reason as the description), or nil when it returned normally.
///
/// Swift cannot catch an `NSException`: one raised under a Swift frame aborts the
/// process. `AVAudioEngine` raises them for runtime conditions nobody can rule out
/// in advance — `-[AVAudioPlayerNode play]` on an engine a device change has just
/// stopped (the two `SIGABRT`s of `evals/wispr-catchup/`, 2026-09-30).
FOUNDATION_EXPORT NSError * _Nullable WTTry(NS_NOESCAPE void (^block)(void));

NS_ASSUME_NONNULL_END
