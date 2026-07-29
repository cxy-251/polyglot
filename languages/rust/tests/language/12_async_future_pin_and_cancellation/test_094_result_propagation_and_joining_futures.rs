// polyglot-covers: rust.async.result_propagation_join

use polyglot_rust_harness::block_on;
use std::future::Future;
use std::pin::Pin;
use std::task::{Context, Poll};

struct Join2<A: Future + Unpin, B: Future + Unpin> {
    left: A,
    right: B,
    left_output: Option<A::Output>,
    right_output: Option<B::Output>,
}

impl<A, B> Future for Join2<A, B>
where
    A: Future + Unpin,
    B: Future + Unpin,
    A::Output: Unpin,
    B::Output: Unpin,
{
    type Output = (A::Output, B::Output);

    fn poll(self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<Self::Output> {
        let this = self.get_mut();
        if this.left_output.is_none()
            && let Poll::Ready(output) = Pin::new(&mut this.left).poll(context)
        {
            this.left_output = Some(output);
        }
        if this.right_output.is_none()
            && let Poll::Ready(output) = Pin::new(&mut this.right).poll(context)
        {
            this.right_output = Some(output);
        }
        match (this.left_output.take(), this.right_output.take()) {
            (Some(left), Some(right)) => Poll::Ready((left, right)),
            (left, right) => {
                this.left_output = left;
                this.right_output = right;
                Poll::Pending
            }
        }
    }
}

async fn parse(text: &str) -> Result<i32, std::num::ParseIntError> {
    let value = text.parse::<i32>()?;
    Ok(value)
}

#[test]
fn result_question_mark_and_a_small_join_future_keep_failures_explicit() {
    let joined = Join2 {
        left: std::future::ready(2),
        right: std::future::ready(3),
        left_output: None,
        right_output: None,
    };
    assert_eq!(block_on(joined), (2, 3));
    assert_eq!(block_on(parse("42")), Ok(42));
    assert!(block_on(parse("bad")).is_err());
}
