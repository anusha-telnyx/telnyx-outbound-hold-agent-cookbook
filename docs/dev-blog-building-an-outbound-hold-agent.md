# Building an Outbound Hold Agent


# Building an outbound agent is easy until the call goes on hold

The first version of an outbound voice agent seems simple: call a company, listen to the IVR, press the right menu option, and talk to a representative.

Then the call goes on hold.

The AI assistant sits through hold music, silence, queue messages, and repeated wait prompts even though there is no real conversation happening. This will start accumulating AI resources and increasing costs. 

I built the Telnyx Outbound Hold Agent Cookbook around that problem. The goal was to keep the phone call connected while pausing the assistant during hold, then resume with the right context when a human representative answers.

The Telnyx Outbound Hold Agent Cookbook walks you through how to create this in practice. It is a reference pattern for handling the hold period of a phone call allowing a representative AI assistant to join the call when it's actually necessary. This saves the cost of the time between the phone tree and reaching the person who can actually help.

## What is an outbound hold agent?

An outbound hold agent is an AI voice workflow that can make a call and manage the non-conversational parts of that call.

It understands that a business call has phases:

- dialing
- IVR navigation
- menu selection
- queue or hold
- representative pickup
- live conversation
- call completion

The key idea is that the call can stay alive even when the AI assistant pauses. The assistant does not need to spend the entire hold period listening to music, silence, or repeated queue messages. Instead, the backend can keep the call connected, monitor for the moment a human returns, and then restart the assistant with the original goal.

That difference sounds small, but it changes how you design the whole system. You stop thinking about the agent as one continuous conversation and start thinking about it as a call workflow with different modes.

## Why hold matters

Many useful outbound calls are mostly waiting.

Think about calling to confirm a hotel reservation, check appointment availability, reach an insurance or benefits representative, ask a vendor about order status, or navigate a support line. The useful conversation might only last a minute or two. The rest is dialing, menus, queue messages, and hold.

That changes how the agent should work. An outbound agent is not always in a conversation. Sometimes it is listening to an IVR. Sometimes it is waiting in a queue. Sometimes it is finally speaking to a person. Those phases should not all use the same assistant behavior.

When hold is not handled explicitly, the system pays for it in two ways.

The first impact is resource waste. The assistant stays active through hold music, silence, and repeated queue prompts even though there is nothing useful to say or decide.

The second impact is agent complexity. If one assistant owns the entire call, one prompt has to cover every phase: IVR navigation, DTMF, hold behavior, representative pickup, live conversation, and completion. That makes the assistant harder to tune and more likely to miss instructions. Splitting the workflow into an IVR assistant and a representative assistant keeps each agent focused on one job.

The better pattern is to treat hold as its own mode. Hold is not dead air inside the same conversation. It is a different state of the call. During that state, the backend can keep the call connected and monitor for a representative without keeping the full assistant active.

## What this cookbook builds

The cookbook provides a runnable starter for building this pattern with Telnyx.

It shows how to build an outbound agent that can:

- call a target number
- use an IVR-focused assistant before hold
- let the backend own DTMF actions
- detect when the call moves into hold
- stop the active assistant while waiting
- monitor for representative pickup
- start a representative-focused assistant with the original objective and recent context

The cookbook also includes a demo scenario with a fake hotel assistant. That demo is not the main product; it is a controlled workflow that shows how the pattern could work in a production system. Developers can see the full shape of the call before adapting it to a real company phone tree: call out, navigate the menu, wait on hold, detect the representative, and resume with context.

That predictable flow matters because it gives developers a concrete reference point. Once the sample works end to end, the same architecture can be adapted for messier, real-world phone systems.

## Why the architecture uses two assistants

At first, one assistant sounds simpler. Give it one big prompt and ask it to handle everything: IVR navigation, hold behavior, representative conversation, and call completion.

But those jobs are different. The IVR assistant’s job is to listen to automated menus, choose the right path, and request DTMF without overtalking. The representative assistant’s job is to handle live conversation, answer questions, and use approved context to complete the task.

When hold is detected, the backend stops the IVR assistant and switches into transcription-only monitoring. The call stays connected, but the full conversational assistant is not running while the line is waiting. 

When transcription indicates that a representative has returned, the backend starts the representative assistant with the objective and recent context. That keeps each assistant focused and makes the handoff an explicit system event instead of an implied behavior inside one prompt.

## What this taught me about real-world voice agents

The planning phase is where the agent starts to work. Before deciding what the assistant should say, you have to ask what you are trying to achieve and why the system should exist in the first place.

For this cookbook, the goal was not just to make an outbound call. The goal was to avoid keeping an AI assistant active when the call did not need one.

That shaped the workflow: let one assistant handle IVR navigation, pause assistant activity during hold, then bring in a representative-focused assistant when the call becomes interactive again.

The core idea is to build the agent around the whole call, including the parts where nothing useful is being said. Once that base architecture flow is clear, the prompts, tools, and implementation details have a much better shape to follow.
