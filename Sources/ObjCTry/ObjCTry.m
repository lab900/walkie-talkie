#import "ObjCTry.h"

NSError * _Nullable WTTry(NS_NOESCAPE void (^block)(void)) {
    @try {
        block();
        return nil;
    } @catch (NSException *exception) {
        NSMutableDictionary *info = [NSMutableDictionary dictionary];
        info[NSLocalizedDescriptionKey] = exception.reason ?: exception.name;
        info[NSLocalizedFailureReasonErrorKey] = exception.name;
        if (exception.userInfo) info[@"userInfo"] = exception.userInfo;
        return [NSError errorWithDomain:@"NSException" code:0 userInfo:info];
    }
}
